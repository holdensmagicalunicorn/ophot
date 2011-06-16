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
"""Unit tests for the requests module."""
import json
import os
import tempfile
import unittest

from configobj import ConfigObj
from flask import request

from ophot import app
from ophot import before_request
from ophot import init_db
from ophot import site_config
from ophot.requests import add_category
from ophot.requests import change_category
from ophot.requests import change_category_name
from ophot.requests import change_spacing
from ophot.requests import delete_category
from ophot.requests import delete_photo
from ophot.requests import get_categories
from ophot.requests import get_photos
from ophot.requests import swap_display_positions
from ophot.requests import update_personal
from ophot.tests import TestSupport
from ophot.tests import temp_photos


class preserve_site_config:
    """Context manager (for use in a "with" statement) which stores the
    original configuration settings from a file on enter, and rewrites those
    settings on exit.

    """
    def __init__(self):
        """Does nothing."""
        pass

    def __enter__(self):
        """Reads the configuration settings file and stashes it so that it can
        be restored later.

        """
        self.original_config = ConfigObj(app.config['SETTINGS_FILE'])

    def __exit__(self, exception_type, exception_value, traceback):
        """Writes the original configuration settings back to the settings
        file.

        """
        self.original_config.write()


def query_url(base, **kw):
    """Creates a URL with initial part *base* and with query strings given by
    keyword arguments.

    """
    query = '&'.join('{0[0]}={0[1]}'.format(item) for item in kw.iteritems())
    return '{0}?{1}'.format(base, query)


class RequestsTestCase(TestSupport):
    """Test class for the requests module."""

    def test_add_category(self):
        """Test for adding a category."""
        self._login()
        result = self.app.get(query_url('/_add_category', categoryname='foo'))
        result = json.loads(result.data)
        self.assertEqual(True, result['added'])
        self.assertEqual(4, result['categoryid'])
        self.assertEqual('foo', result['categoryname'])

    def test_change_category(self):
        """Test for changing the category of a photo."""
        self._login()
        with temp_photos():
            url = query_url('/_change_category', photoid=1, categoryid=3)
            result = json.loads(self.app.get(url).data)
            self.assertEqual(True, result['changed'])
            self.assertEqual(1, int(result['photoid']))
            self.assertEqual(3, int(result['categoryid']))
            # get the photos by category
            url = (query_url('/_get_photos', categoryid=n+1) for n in range(3))
            photos = (json.loads(self.app.get(u).data) for u in url)
            # each category should have just one photo now
            for p in photos:
                self.assertEqual(1, len(p['values']))

            # now test adding a new category
            url = query_url('/_change_category', photoid=1, categoryid=-1,
                            categoryname='foo')
            result = json.loads(self.app.get(url).data)
            self.assertEqual(True, result['changed'])
            self.assertEqual(1, int(result['photoid']))
            self.assertEqual(4, int(result['categoryid']))
            # get the photos by category (category 3 should have 0 now)
            url = (query_url('/_get_photos', categoryid=n) for n in (1,2,4))
            photos = (json.loads(self.app.get(u).data) for u in url)
            # each category should have just one photo now
            for p in photos:
                self.assertEqual(1, len(p['values']))
            url = query_url('/_get_photos', categoryid=3)
            photos = json.loads(self.app.get(url).data)
            self.assertEqual(0, len(photos['values']))


    def test_change_category_name(self):
        """Tests changing the name of a category."""
        self._login()
        with temp_photos():
            url = query_url('/_get_photos', categoryid=1)
            photos_before = json.loads(self.app.get(url).data)
            url = query_url('/_change_category_name', categoryid=1,
                            categoryname='foo')
            result = json.loads(self.app.get(url).data)
            self.assertEqual(True, result['changed'])
            self.assertEqual(1, int(result['categoryid']))
            self.assertEqual('foo', result['categoryname'])
            url = query_url('/_get_photos', categoryid=1)
            photos_after = json.loads(self.app.get(url).data)
            self.assertEqual(photos_before, photos_after)
            url = query_url('/_get_categories')
            categories = json.loads(self.app.get(url).data)
            self.assertEqual('foo', categories['1'])
            self.assertEqual('personal', categories['2'])
            self.assertEqual('portrait', categories['3'])

    def test_change_spacing(self):
        """Tests changing the spacing (in pixels) between photos on the splash
        page.

        """
        self._login()
        with preserve_site_config():
            result = json.loads(self.app.get(query_url('/_change_spacing', spacing=123)).data)
            self.assertTrue(result['changed'])
            self.assertEqual(123, site_config['SPACING'])
