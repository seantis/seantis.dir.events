import re
import mock

from datetime import datetime, timedelta
from seantis.dir.events import dates
from seantis.dir.events.tests import BrowserTestCase


class CommonBrowserTests(BrowserTestCase):

    def test_workflow(self):

        # anonymous browser
        fourchan = self.new_browser()
        fourchan.open('/veranstaltungen/@@submit')

        self.assertTrue('Send us your events' in fourchan.contents)

        # create some event
        def create_event():
            fourchan.getControl(name='form.widgets.title').value = 'Party'
            fourchan.getControl(
                name='form.widgets.short_description'
            ).value = 'Some Party'

            fourchan.set_date('form.widgets.submission_date', datetime.now())
            fourchan.getControl(
                name='form.widgets.submission_start_time'
            ).value = '08:00 AM'
            fourchan.getControl(
                name='form.widgets.submission_end_time'
            ).value = '12:00 PM'

            fourchan.getControl('Category1').selected = True
            fourchan.getControl('Category2').selected = True

            fourchan.getControl('Continue').click()
            self.assertTrue('preview' in fourchan.url)
            fourchan.getControl('Continue').click()
            self.assertTrue('finish' in fourchan.url)

            fourchan.getControl(
                name='form.widgets.submitter'
            ).value = 'John Doe'
            fourchan.getControl(
                name='form.widgets.submitter_email'
            ).value = 'john.doe@example.com'

            fourchan.getControl('Submit').click()

        create_event()

        # the event is now invisible to the anonymous user in the directory
        fourchan.open('/veranstaltungen?state=submitted')
        self.assertFalse('Some Party' in fourchan.contents)

        # it is however visible to the admin
        browser = self.admin_browser
        browser.open('/veranstaltungen?state=submitted')

        self.assertTrue('Some Party' in browser.contents)

        browser = self.admin_browser
        browser.open('/veranstaltungen?state=submitted')

        self.assertTrue('Some Party' in browser.contents)

        # unless the admin filters it out
        browser.open('/veranstaltungen?state=published')

        self.assertFalse('Some Party' in browser.contents)

        # who now has the chance to either deny or publish the event
        browser.open('/veranstaltungen?state=submitted')
        self.assertTrue('Publish' in browser.contents)
        self.assertTrue('Deny Publication' in browser.contents)
        self.assertTrue('Submitted' in browser.contents)

        # let's deny
        browser.getLink('Deny Publication').click()

        # the event should now be invisible to both admin and anonymous
        browser.open('/veranstaltungen')
        self.assertFalse('Some Party' in browser.contents)

        fourchan.open(browser.url)
        self.assertFalse('Some Party' in browser.contents)

        # let's repeat, but publish this time
        fourchan.open('/veranstaltungen/@@submit')
        create_event()

        browser.open('/veranstaltungen?state=submitted')
        browser.getLink('Publish', index=1).click()

        # this should've led to a state change
        browser.open('/veranstaltungen?state=published')
        self.assertTrue('Some Party' in browser.contents)
        self.assertTrue('Archive' in browser.contents)

        fourchan.open(browser.url)
        self.assertTrue('Some Party' in fourchan.contents)
        self.assertFalse('Archive' in fourchan.contents)

        # archiving the event should hide it again
        browser.getLink('Archive', index=1).click()
        browser.open('/veranstaltungen')

        self.assertFalse('Some Party' in browser.contents)

        fourchan.open(browser.url)
        self.assertFalse('SomeParty' in browser.contents)

        # archive it permanently (both events)
        browser.open('/veranstaltungen?state=archived')
        self.assertTrue('Some Party' in browser.contents)
        self.assertTrue('Archive permanently' in browser.contents)
        browser.getLink('Archive permanently').click()

        browser.open('/veranstaltungen?state=archived')
        self.assertTrue('Some Party' in browser.contents)
        self.assertTrue('Archive permanently' in browser.contents)
        browser.getLink('Archive permanently').click()

        browser.open('/veranstaltungen?state=archived')
        self.assertFalse('Some Party' in browser.contents)

    def test_preview(self):

        # anonymous browser
        fourchan = self.new_browser()
        fourchan.open('/veranstaltungen/@@submit')

        self.assertTrue('Send us your events' in fourchan.contents)

        # create a recurring event
        fourchan.widget('title').value = 'Recurring'
        fourchan.widget('short_description').value = 'Every Day'
        fourchan.widget('locality').value = 'at home'

        fourchan.set_date('submission_date', datetime.now())

        fourchan.widget('submission_start_time').value = '08:00 AM'
        fourchan.widget('submission_end_time').value = '04:00 PM'

        fourchan.getControl('Category1').selected = True
        fourchan.getControl('Category2').selected = True

        fourchan.widget(
            'submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;COUNT=7'

        fourchan.getControl('Continue').click()
        self.assertTrue('preview' in fourchan.url)

        # expect all fields to be shown and the recurrence resulting in
        # a number of events in the list

        self.assertTrue('Recurring' in fourchan.contents)
        self.assertTrue('Every Day' in fourchan.contents)
        self.assertTrue('at home' in fourchan.contents)
        self.assertEqual(fourchan.contents.count('"eventgroup"'), 7)

        # update the recurrence and check back
        fourchan.getControl('Adjust').click()

        fourchan.widget(
            'submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;COUNT=365'

        fourchan.getControl('Continue').click()

        self.assertEqual(fourchan.contents.count('"eventgroup"'), 365)

        # remove the recurrence, ensuring that one event remains
        fourchan.getControl('Adjust').click()

        fourchan.widget('submission_recurrence').value = ''
        fourchan.getControl('Continue').click()

        self.assertEqual(fourchan.contents.count('"eventgroup"'), 1)

        # ensure that no more than 365 occurrences may be entered
        fourchan.getControl('Adjust').click()
        fourchan.widget(
            'submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;COUNT=366'

        fourchan.getControl('Continue').click()

        self.assertTrue(
            'You may not add more than 365 occurences' in fourchan.contents
        )

        # regression test for an issue where occurrences in the future
        # were not counted correctly
        fourchan.set_date('submission_date', datetime(2021, 1, 1, 0, 0))
        fourchan.widget('submission_start_time').value = '10:00 AM'
        fourchan.widget('submission_end_time').value = '11:00 AM'

        fourchan.widget(
            'submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;UNTIL=20211231T000000'

        fourchan.getControl('Continue').click()  # ok

        self.assertFalse(
            'You may not add more than 365 occurences' in fourchan.contents
        )

        fourchan.getControl('Adjust').click()

        fourchan.widget(
            'submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;UNTIL=20220101T000000'

        fourchan.getControl('Continue').click()  # not okay

        self.assertTrue(
            'You may not add more than 365 occurences' in fourchan.contents
        )

    def test_event_submission(self):

        browser = self.admin_browser

        # get a browser for anonymous
        fourchan = self.new_browser()
        fourchan.open('/veranstaltungen')

        self.assertTrue('Veranstaltungen' in browser.contents)

        # get to the submit form
        fourchan.getLink('Submit Your Event').click()

        self.assertTrue('Send us your events' in fourchan.contents)

        fourchan.getControl(name='form.widgets.title').value = 'Stammtisch'
        fourchan.getControl(
            name='form.widgets.short_description'
        ).value = 'Socializing Yo'

        fourchan.set_date('form.widgets.submission_date', datetime.now())
        fourchan.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        fourchan.getControl(
            name='form.widgets.submission_end_time'
        ).value = '12:00 AM'

        fourchan.getControl('Category1').selected = True
        fourchan.getControl('Category2').selected = True

        fourchan.getControl('Continue').click()

        # previewing an event should send us to the preview view
        self.assertTrue('preview' in fourchan.url)

        # a token should have been added to the url
        self.assertTrue('token=' in fourchan.url)

        # the preview should contain the entered information
        self.assertTrue('Socializing Yo' in fourchan.contents)

        # if the user tries to submit another event while this one is still
        # in preview, the existing event is loaded
        # (the form is turned into an edit form)
        oldurl = fourchan.url

        fourchan.open('/veranstaltungen/@@submit')
        self.assertEqual(
            fourchan.getControl(name='form.widgets.title').value,
            'Stammtisch'
        )
        self.assertEqual(
            fourchan.getControl(name='form.widgets.short_description').value,
            'Socializing Yo'
        )

        fourchan.open(oldurl)

        # there's a change-event button which submits a GET request to
        # the submit form using the token in the request
        fourchan.getControl('Adjust').click()
        self.assertTrue('submit?token=' in fourchan.url)
        self.assertFalse(fourchan.url.endswith('?token='))

        # we should be able to change some things
        # and come back to the url to find those changes

        fourchan.getControl(
            name='form.widgets.short_description'
        ).value = 'Serious Business'
        fourchan.getControl('Continue').click()

        self.assertTrue('Serious Business' in fourchan.contents)
        self.assertTrue('preview' in fourchan.url)

        # at the same time this event in preview is invisble in the list
        # even for administrators
        browser.open('/veranstaltungen')
        self.assertTrue('Veranstaltungen' in browser.contents)
        self.assertFalse('Serious Business' in browser.contents)

        # other anonymous users may not access the view or the preview
        google_robot = self.new_browser()
        google_robot.assert_notfound('/veranstaltungen/stammtisch')
        google_robot.assert_notfound(
            '/veranstaltungen/stammtisch/preview'
        )

        # not event the admin at this point (not sure about that one yet)
        browser.assert_notfound('/veranstaltungen/stammtisch')
        browser.assert_notfound(
            '/veranstaltungen/stammtisch/preview'
        )

        # if the user decides to cancel the event before submitting it, he
        # loses the right to access the event (will be cleaned up by cronjob)
        fourchan.getControl('Cancel').click()

        fourchan.assert_notfound('/veranstaltungen/stammtisch')
        fourchan.assert_notfound(
            '/veranstaltungen/stammtisch/preview'
        )
        fourchan.assert_notfound(
            '/veranstaltungen/stammtisch/edit-event'
        )

        # since we cancelled we must now create a new event to
        # test the submission process
        new = self.new_browser()
        new.open('/veranstaltungen/@@submit')

        self.assertEqual(new.getControl(name='form.widgets.title').value, '')
        self.assertEqual(
            new.getControl(name='form.widgets.short_description').value, ''
        )

        new.set_date('form.widgets.submission_date', datetime.now())
        new.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        new.getControl(
            name='form.widgets.submission_end_time'
        ).value = '12:00 AM'

        new.getControl('Category1').selected = True
        new.getControl('Category2').selected = True

        new.getControl(name='form.widgets.title').value = "Submitted Event"
        new.getControl(name='form.widgets.short_description').value = "YOLO"

        new.getControl('Continue').click()

        # at this point the event is invisble to the admin
        browser.open('/veranstaltungen?state=submitted')
        self.assertFalse('YOLO' in browser.contents)

        # until the anonymous user submits the event
        new.getControl('Continue').click()

        new.getControl('Submit').click()

        # at this point we 'forgot' to fill in the submitter info so we have at
        # it again and fix that
        new.getControl(name='form.widgets.submitter').value = 'John Doe'
        new.getControl(
            name='form.widgets.submitter_email'
        ).value = 'john.doe@example.com'

        new.getControl('Submit').click()

        browser.open('/veranstaltungen?state=submitted')
        self.assertTrue('YOLO' in browser.contents)

        # the user may no longer access the event at this point, though
        # it is no longer an inexistant resource
        new.assert_unauthorized('/veranstaltungen/submitted-event')

        # the admin should be able to see the submitter's name and email
        browser.open('/veranstaltungen/submitted-event')
        self.assertTrue('John Doe' in browser.contents)
        self.assertTrue('john.doe@example.com' in browser.contents)

        # once we publish it and open in another browser this information is
        # hidden from the public eye
        url = browser.url
        browser.open((
            '/veranstaltungen/submitted-event'
            '/content_status_modify?workflow_action=publish'
        ))

        public = self.new_browser()
        public.open(url)

        self.assertTrue('YOLO' in public.contents)
        self.assertFalse('John Doe' in public.contents)
        self.assertFalse('john.doe@example.com' in public.contents)

    def test_simplified_recurrence_submission(self):
        browser = self.admin_browser
        browser.open('/veranstaltungen/++add++seantis.dir.events.item')

        browser.widget('title').value = 'Testtitle'
        browser.widget('short_description').value = 'Testdescription'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.widget('submission_date_type').value = ['range']

        start = datetime.today()
        end = start + timedelta(days=2)

        browser.set_date('submission_range_start_date', start)
        browser.set_date('submission_range_end_date', end)
        browser.widget('submission_range_start_time').value = '2:00 PM'
        browser.widget('submission_range_end_time').value = '4:00 PM'

        browser.getControl('Continue').click()

        self.assertTrue('3 Occurrences' in browser.contents)

        browser.getControl('Adjust').click()

        browser.set_date('submission_range_end_date', end - timedelta(days=1))

        browser.getControl('Continue').click()

        self.assertTrue('2 Occurrences' in browser.contents)

        browser.getControl('Adjust').click()

        browser.widget('submission_date_type').value = ['date']
        browser.set_date('submission_date', start)
        browser.widget('submission_start_time').value = '2:00 PM'
        browser.widget('submission_end_time').value = '4:00 PM'
        browser.widget('submission_recurrence').value = ''

        browser.getControl('Continue').click()

        self.assertTrue('No Occurrences' in browser.contents)

        browser.getControl('Adjust').click()
        browser.widget('submission_date_type').value = ['range']
        browser.set_date('submission_range_start_date', start)
        browser.set_date('submission_range_end_date', start)

        browser.getControl('Continue').click()

        self.assertTrue('No Occurrences' in browser.contents)

    def test_simplified_recurrence_submission_days(self):
        browser = self.admin_browser
        browser.open('/veranstaltungen/++add++seantis.dir.events.item')

        browser.widget('title').value = 'Testtitle'
        browser.widget('short_description').value = 'Testdescription'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.widget('submission_date_type').value = ['range']

        # get a monday to test with
        start = datetime.now()
        while start.weekday() != 0:
            start += timedelta(days=1)

        end = start + timedelta(days=6)  # sunday

        browser.set_date('submission_range_start_date', start)
        browser.set_date('submission_range_end_date', end)
        browser.widget('submission_range_start_time').value = '2:00 PM'
        browser.widget('submission_range_end_time').value = '4:00 PM'
        browser.widget('submission_days:list').value = ['MO', 'SU']

        browser.getControl('Continue').click()
        self.assertTrue('2 Occurrences' in browser.contents)

        browser.getControl('Adjust').click()
        browser.widget('submission_days:list').value = ['MO', 'WE', 'SU']

        browser.getControl('Continue').click()
        self.assertTrue('3 Occurrences' in browser.contents)

        browser.getControl('Adjust').click()
        browser.widget('submission_days:list').value = []

        browser.getControl('Continue').click()
        self.assertTrue('No Occurrences' in browser.contents)

    def test_default_forms(self):

        # admins use the submit / preview forms for adding / editing
        # as well so we don't have to support two different form types
        # the following code tests that
        browser = self.admin_browser

        browser.open('/veranstaltungen/++add++seantis.dir.events.item')
        self.assertTrue('Send us your events' in browser.contents)

        browser.getControl(name='form.widgets.title').value = 'Add Test'
        browser.getControl(
            name='form.widgets.short_description'
        ).value = 'Add Test Description'

        browser.set_date('form.widgets.submission_date', datetime.now())
        browser.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        browser.getControl(
            name='form.widgets.submission_end_time'
        ).value = '04:00 PM'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.getControl('Continue').click()
        self.assertTrue('preview' in browser.url)

        self.assertTrue('Add Test Description' in browser.contents)

        browser.getControl('Continue').click()
        self.assertTrue('finish' in browser.url)

        browser.getControl('Submitter Name').value = 'Submitter'
        browser.getControl('Submitter Email').value = 'submit@example.com'

        browser.getControl('Submit').click()

        # show the submitted events
        browser.getLink('Submitted').click()

        self.assertTrue('Add Test Description' in browser.contents)
        self.assertTrue('Veranstaltungen' in browser.contents)

        browser.open('/veranstaltungen/add-test/edit')
        self.assertTrue('Send us your events' in browser.contents)

        browser.getControl(
            name='form.widgets.short_description'
        ).value = 'Changed Test Description'
        browser.getControl('Save Event').click()

        self.assertTrue('Changed Test Description' in browser.contents)
        self.assertFalse('preview' in browser.url)

    def test_recurrence(self):
        browser = self.admin_browser

        browser.open(
            '/veranstaltungen/++add++seantis.dir.events.item'
        )
        self.assertTrue('Send us your events' in browser.contents)

        browser.getControl(name='form.widgets.title').value = 'Recurring'
        browser.getControl(
            name='form.widgets.short_description'
        ).value = 'Add Test Description'
        browser.getControl(
            name='form.widgets.submission_recurrence'
        ).value = 'RRULE:FREQ=DAILY;COUNT=7'

        browser.set_date('form.widgets.submission_date', datetime.now())
        browser.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        browser.getControl(
            name='form.widgets.submission_end_time'
        ).value = '04:00 PM'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.getControl('Continue').click()
        browser.getControl('Continue').click()

        browser.getControl('Submitter Name').value = 'Submitter'
        browser.getControl('Submitter Email').value = 'submit@example.com'

        browser.getControl('Submit').click()

        # make sure to get all events
        browser.getLink('This and Next Year').click()

        # with the state submitted
        browser.getLink('Submitted').click()

        # take the last occurrence
        first_url = browser.getLink('Recurring', index=0).url
        link = browser.getLink('Recurring', index=6)
        year, month, day = map(
            int, link.url[len(link.url) - 10:].split('-')
        )

        # and ensure that the date is correct in the detail view
        link.click()

        self.assertFalse('Today' in browser.contents)
        self.assertTrue('%02i.%02i' % (day, month) in browser.contents)

        browser.open(first_url)
        self.assertTrue('Today' in browser.contents)

        # replace the date in the url with an invalid date -> 404
        first_url = re.sub('\d{4}-\d{2}-\d{2}', r'2000-01-01', first_url)
        browser.assert_notfound(first_url)

    def test_wrong_dates(self):
        browser = self.admin_browser

        # Missing start time
        browser.open('/veranstaltungen/@@submit')
        browser.widget('title').value = 'Title'
        browser.widget('short_description').value = 'Description'
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.set_date('form.widgets.submission_date',
                         datetime.now() + timedelta(days=2))
        browser.getControl(
            name='form.widgets.submission_end_time'
        ).value = '12:00 PM'
        browser.getControl('Continue').click()
        self.assertTrue('Missing start time' in browser.contents)

        # Missing end time
        browser.open('/veranstaltungen/@@submit')
        browser.widget('title').value = 'Title'
        browser.widget('short_description').value = 'Description'
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.set_date('form.widgets.submission_date',
                         datetime.now() + timedelta(days=2))
        browser.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        browser.getControl('Continue').click()
        self.assertTrue('Missing end time' in browser.contents)

    def test_coordinates(self):
        browser = self.admin_browser

        # Invalid coordinates
        browser.open('/veranstaltungen/@@submit')
        browser.widget('title').value = 'event with coordinates'
        browser.widget('short_description').value = 'Short'
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.set_date('form.widgets.submission_date',
                         datetime.now() + timedelta(days=2))
        browser.getControl('All day').selected = True
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.getControl(
            name="form.widgets.wkt"
        ).value = "PINT (8.3156129 47.05033479999997)"
        click = lambda: browser.getControl('Continue').click()
        self.assertRaises(Exception, click)

        # Valid coordinates
        browser.open('/veranstaltungen/@@submit')
        browser.widget('title').value = 'event with coordinates'
        browser.widget('short_description').value = 'Short'
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.set_date('form.widgets.submission_date',
                         datetime.now() + timedelta(days=2))
        browser.getControl('All day').selected = True
        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True
        browser.getControl(
            name="form.widgets.wkt"
        ).value = "POINT (8.3156129 47.05033479999997)"
        browser.getControl('Continue').click()
        browser.getControl('Continue').click()
        browser.getControl('Submitter Name').value = 'Submitter'
        browser.getControl('Submitter Email').value = 'submit@example.com'
        browser.getControl('Submit').click()

        browser.open('/veranstaltungen/event-with-coordinates/edit')
        self.assertTrue(
            "POINT (8.3156129 47.05033479999997)" in browser.contents
        )

    def test_terms(self):
        browser = self.admin_browser

        def enable_terms(enable):
            new = self.new_browser()
            new.login_admin()

            new.open('/veranstaltungen/edit')
            new.getControl(
                name="form.widgets.terms"
            ).value = enable and 'verily, though agreeth' or ''
            new.getControl('Save').click()

        browser.open(
            '/veranstaltungen/++add++seantis.dir.events.item'
        )
        self.assertTrue('Send us your events' in browser.contents)

        browser.getControl(name='form.widgets.title').value = 'Test'
        browser.getControl(
            name='form.widgets.short_description'
        ).value = 'Test'

        browser.set_date('form.widgets.submission_date', datetime.now())
        browser.getControl(
            name='form.widgets.submission_start_time'
        ).value = '08:00 AM'
        browser.getControl(
            name='form.widgets.submission_end_time'
        ).value = '04:00 PM'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.getControl('Continue').click()
        browser.getControl('Continue').click()

        self.assertFalse('Terms and Conditions' in browser.contents)

        enable_terms(True)

        browser.reload()
        self.assertTrue('Terms and Conditions' in browser.contents)

        browser.getLink('Terms and Conditions').click()
        self.assertTrue('verily' in browser.contents)

        browser.goBack()

        # if not agreed upon, the submission is denied
        browser.getControl('Submitter Name').value = 'Submitter'
        browser.getControl('Submitter Email').value = 'submit@example.com'
        self.assertTrue('Terms and Conditions' in browser.contents)

        browser.getControl('Submit').click()
        self.assertTrue('finish' in browser.url)
        self.assertTrue('Terms and Conditions' in browser.contents)

        browser.getControl(name='form.widgets.agreed:list').value = 'selected'
        browser.getControl('Submit').click()

        self.assertFalse('finish' in browser.url)
        self.assertFalse('Terms and Conditions' in browser.contents)
        self.assertTrue('Event submitted' in browser.contents)

    @mock.patch('seantis.dir.events.dates.default_timezone')
    @mock.patch('seantis.dir.events.dates.default_now')
    def test_whole_day_regression(self, default_now, default_timezone):
        # recurring whole day events would lead to errors because the
        # daterange applied in the catalog did not include 00:00 one day
        # after creating the event

        # the error only happens if the timezone of the event and the
        # server differs

        default_timezone.return_value = 'Europe/Vienna'
        default_now.return_value = dates.as_timezone(
            datetime.now(), 'Europe/Vienna'
        )

        browser = self.admin_browser

        # create the event in europe/vienna timezone
        browser.open(
            '/veranstaltungen/++add++seantis.dir.events.item'
        )

        browser.widget('title').value = 'Title'
        browser.widget('short_description').value = 'Short'

        browser.getControl('Category1').selected = True
        browser.getControl('Category2').selected = True

        browser.widget('submission_date_type').value = ['range']

        start = datetime.now()
        end = datetime.now() + timedelta(days=2)

        browser.set_date('submission_range_start_date', start)
        browser.set_date('submission_range_end_date', end)
        browser.getControl('All day').selected = True

        browser.getControl('Continue').click()
        browser.getControl('Continue').click()

        browser.widget('submitter').value = 'test'
        browser.widget('submitter_email').value = 'test@example.com'

        browser.getControl('Submit').click()

        # view the event the next day in UTC
        default_timezone.return_value = 'UTC'
        default_now.return_value = dates.as_timezone(
            datetime.now() + timedelta(days=1), 'Europe/Vienna'
        )

        # this used to throw an error
        browser.open('/veranstaltungen?state=submitted')

    def test_filter_and_search(self):
        # Add events
        self.addEvent(title='test1', description='desc1')
        self.addEvent(title='test2', description='desc2',
                      cat1='Category1_2', cat2='Category2_2')

        browser = self.new_browser()

        # No categories, no filter
        browser.open('/veranstaltungen')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # Filter (&filter=&cat1=&cat2=)
        browser.open('/veranstaltungen?filter=true&cat1=Category1')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?filter=true&cat1=Category1_2')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?filter=true&cat2=Category2_2')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?filter=true&cat1=Category2_2')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        # Search (search=&searchtext=)
        browser.open('/veranstaltungen?search=true&searchtext=test1')
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        browser.open('/veranstaltungen?search=true&searchtext=test2')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' in browser.contents)

        browser.open('/veranstaltungen?search=true&searchtext=token')
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

    def test_eventindex_view(self):
        # Test unauthorized access
        anonymous = self.new_browser()
        anonymous.assert_unauthorized('/veranstaltungen/eventindex')

        browser = self.admin_browser

        # Test eventindex
        browser.open('/veranstaltungen/eventindex')
        self.assertTrue('text/plain' in browser.headers['Content-type'])
        self.assertTrue('test1' not in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        self.addEvent(title='test1')
        browser.open('/veranstaltungen/eventindex')
        self.assertTrue('text/plain' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' not in browser.contents)

        self.addEvent(title='test2')
        browser.open('/veranstaltungen/eventindex')
        self.assertTrue('text/plain' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # reindex
        browser.open('/veranstaltungen/eventindex?reindex')
        self.assertTrue('text/plain' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

        # rebuild
        browser.open('/veranstaltungen/eventindex?rebuild')
        self.assertTrue('text/plain' in browser.headers['Content-type'])
        self.assertTrue('test1' in browser.contents)
        self.assertTrue('test2' in browser.contents)

    def test_browser_add_today_whole_day(self):
        browser = self.admin_browser

        self.addEvent(title='whole-day-event-today',
                      whole_day=True,
                      check_submitted=False, do_publish=False)

        browser.open('/veranstaltungen?state=submitted')

        # The event should be visible (it wasn't in an earlier version)
        self.assertTrue('whole-day-event-today' in browser.contents)
        self.assertTrue('Submitted (1)' in browser.contents)

        # .. .also if published
        browser.getLink('Publish', index=1).click()
        browser.open('/veranstaltungen?state=published')
        self.assertTrue('whole-day-event-today' in browser.contents)

    def test_date_range_selection(self):
        browser = self.admin_browser

        def open_range(date1, date2):
            browser.open(
                'veranstaltungen?range=custom&from=%s&to=%s' % (
                    '%04i-%02i-%02i' % (date1.year, date1.month, date1.day),
                    '%04i-%02i-%02i' % (date2.year, date2.month, date2.day)
                )
            )

        dates = [datetime.today() + timedelta(days=d) for d in [8, 15, 28, 45]]
        for date in dates:
            self.addEvent(title=str(date), date=date)

        open_range(datetime.today(), dates[2])
        self.assertTrue(str(dates[0]) in browser.contents)
        self.assertTrue(str(dates[1]) in browser.contents)
        self.assertTrue(str(dates[2]) in browser.contents)
        self.assertFalse(str(dates[3]) in browser.contents)

        open_range(dates[1], dates[3])
        self.assertFalse(str(dates[0]) in browser.contents)
        self.assertTrue(str(dates[1]) in browser.contents)
        self.assertTrue(str(dates[2]) in browser.contents)
        self.assertTrue(str(dates[3]) in browser.contents)

        open_range(dates[3], dates[2])
        self.assertFalse(str(dates[0]) in browser.contents)
        self.assertFalse(str(dates[1]) in browser.contents)
        self.assertFalse(str(dates[2]) in browser.contents)
        self.assertTrue(str(dates[3]) in browser.contents)

    def test_cleanup_view(self):
        browser = self.admin_browser
        browser.open('veranstaltungen/cleanup?run=1')

    def test_fetch_view(self):
        browser = self.admin_browser
        browser.open('veranstaltungen/fetch')
