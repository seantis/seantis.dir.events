import pytz

from datetime import datetime, timedelta
from dateutil.tz import tzlocal

from seantis.dir.events.tests import BrowserTestCase


class CommonBrowserTests(BrowserTestCase):

    def test_json_export(self):
        # Add events
        self.addEvent(title='test1', description='desc1')
        self.addEvent(title='test2', description='desc2',
                      cat1='Category1_2', cat2='Category2_2',
                      recurrence='RRULE:FREQ=DAILY;COUNT=2')
        first_date = datetime.now(tzlocal()).replace(
            hour=14, minute=0, second=0, microsecond=0
        ).astimezone(pytz.utc)
        second_date = first_date + timedelta(days=1)

        browser = self.new_browser()

        # Export all
        browser.open('/veranstaltungen?type=json')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)
        self.assertTrue('desc1' in browser.contents)
        self.assertTrue('desc2' in browser.contents)
        self.assertTrue('Category1' in browser.contents)
        self.assertTrue('Category1_2' in browser.contents)
        self.assertTrue('Category2' in browser.contents)
        self.assertTrue('Category2_2' in browser.contents)
        self.assertTrue(first_date.isoformat() in browser.contents)
        self.assertTrue(second_date.isoformat() in browser.contents)

        # Export compact
        browser.open('/veranstaltungen?type=json&compact=1')
        self.assertTrue('RRULE:FREQ=DAILY;COUNT=2' in browser.contents)
        self.assertTrue(first_date.isoformat() in browser.contents)
        self.assertTrue(second_date.isoformat() not in browser.contents)

        # Export by using filter (&filter=&cat1=&cat2=)
        browser.open('/veranstaltungen?type=json&filter=true&cat1=Category1')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=json&filter=true&cat1=Category1_2')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=json&filter=true&cat2=Category2_2')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=json&filter=true&cat1=C1&cat2=C2')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=json&cat1=Category1')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Export by using search (search=&searchtext=)
        browser.open('/veranstaltungen?type=json&search=true&searchtext=test1')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=json&search=true&searchtext=test2')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=json&search=true&searchtext=test7')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=json&searchtext=test1')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Export only first event
        browser.open('/veranstaltungen?type=json&max=1')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

    def test_issue_17(self):
        self.addEvent(title='test1')
        self.addEvent(title='test2', date=datetime.today() - timedelta(days=2),
                      check_submitted=False, do_publish=False)
        self.addEvent(title='test3', date=datetime.today() - timedelta(days=4),
                      check_submitted=False, do_publish=False)
        self.admin_browser.open(
            '/veranstaltungen/test3/do-action?action=publish')

        # Past events (submitted or published) should not be exported
        browser = self.new_browser()
        browser.open('/veranstaltungen?type=json')
        self.assertEqual(browser.headers['Content-type'], 'application/json')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)
        self.assertTrue('test3' not in browser.contents)

    def test_ical_export(self):
        # Add events
        self.addEvent(title='test1', description='desc1')
        self.addEvent(title='test2', description='desc2',
                      cat1='Category1_2', cat2='Category2_2')

        browser = self.new_browser()

        # Export all
        browser.open('/veranstaltungen?type=ical')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Export by using filter (&filter=&cat1=&cat2=)
        browser.open('/veranstaltungen?type=ical&filter=true&cat1=Category1')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=ical&filter=true&cat1=Category1_2')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=ical&filter=true&cat2=Category2_2')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=ical&filter=true&cat1=C1&cat2=C2')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=ical&cat1=Category1')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Export by using search (search=&searchtext=)
        browser.open('/veranstaltungen?type=ical&search=true&searchtext=test1')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=ical&search=true&searchtext=test2')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?type=ical&search=true&searchtext=test7')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?type=ical&searchtext=test1')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Export via item view
        browser.open('/veranstaltungen/test1?type=ical')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)

        browser.open('/veranstaltungen/test2?type=ical')
        self.assertTrue('text/calendar' in browser.headers['Content-type'])
        self.assertTrue('test2' in browser.contents)
