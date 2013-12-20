import re
import mock

from datetime import datetime, timedelta
from seantis.dir.events import dates
from seantis.dir.events.tests import BrowserTestCase


class CommonBrowserTests(BrowserTestCase):

    def addGuidleSource(
        self, title='title', url='http://localhost:8888/',
        interval='daily', enabled=True, do_check_saved=True):

        browser = self.admin_browser

        # Add form
        browser.open('/veranstaltungen/++add++seantis.dir.events.sourceguidle')
        browser.widget('title').value = title
        browser.widget('url').value = url
        browser.getControl('Enabled').selected = enabled
        if interval == 'daily':
            browser.getControl('Every day').selected = True
        elif interval == 'hourly':
            browser.getControl('Every hour').selected = True

        # Save
        browser.getControl('Save').click()

        # Check if saved
        browser.open('/veranstaltungen/')
        self.assertTrue(title in browser.contents)

    def test_browser_add_guidle_source(self):
        self.addGuidleSource(url='')
