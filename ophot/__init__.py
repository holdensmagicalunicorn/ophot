# Copyright 2011 Jeffrey Finkelstein
#
# This file is part of Ophot.
#
# Ophot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ophot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Ophot.  If not, see <http://www.gnu.org/licenses/>.
"""
Provides general functions needed for all other modules in this package, and
allows this directory to be treated as a Python package.

"""
# imports for compatibility with future python versions
from __future__ import absolute_import
from __future__ import division

# imports from built-in modules
from contextlib import closing
import sqlite3

# imports from third party modules
from configobj import ConfigObj
from flask import Flask
from flask import g

# create the application and get app configuration from config.py, or a file
app = Flask('ophot')
app.config.from_object('ophot.config')
app.config.from_envvar('OPHOT_SETTINGS', silent=True)

# site-wide configuration which is not necessary for running the app
site_config = ConfigObj(app.config['SETTINGS_FILE'])
if 'BIO' not in site_config:
    site_config['BIO'] = ''
if 'CONTACT' not in site_config:
    site_config['CONTACT'] = ''
if 'SPACING' not in site_config:
    site_config['SPACING'] = app.config['DEFAULT_PHOTO_SPACING']

# add some loggers for errors and warnings
if not app.debug:
    from logging import ERROR
    from logging import WARNING
    from logging import FileHandler
    from logging import Formatter
    from logging.handlers import SMTPHandler
    sender_address = 'server-error@{0}'.format(app.config['DOMAIN_NAME'])
    mail_handler = SMTPHandler('127.0.0.1', sender_address,
                               app.config['ERROR_MAIL_RECIPIENTS'],
                               app.config['ERROR_MAIL_SUBJECT'])
    mail_handler.setFormatter(Formatter('''
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s

Message:

%(message)s
'''))
    # email us if something goes really wrong
    mail_handler.setLevel(ERROR)
    app.logger.addHandler(mail_handler)
    # write to a file on warnings
    file_handler = FileHandler(app.config['LOGFILE'])
    file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
            ' [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(WARNING)
    app.logger.addHandler(file_handler)


@app.after_request
def after_request(response):
    """Closes the database connection stored in the db attribute of the g
    object.

    The response to the request is returned unchanged.

    """
    g.db.close()
    return response


@app.before_request
def before_request():
    """Stores the database connection in the db attribute of the g object."""
    g.db = connect_db()


def connect_db():
    """Gets a connection to the SQLite database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Initialize the database using the schema specified in the configuration.

    """
    with closing(connect_db()) as db:
        with app.open_resource(app.config['SCHEMA']) as f:
            db.cursor().executescript(f.read())
        db.commit()


import ophot.user
import ophot.photos
import ophot.categories
import ophot.views
