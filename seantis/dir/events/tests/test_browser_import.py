import mock

from datetime import datetime, timedelta

from plone.app.event.base import default_timezone

from seantis.dir.events.tests import BrowserTestCase
from seantis.dir.events.dates import default_now


class CommonBrowserTests(BrowserTestCase):

    def create_fetch_entry(self, **kw):
        def_start = datetime.today().replace(second=0) + timedelta(days=10)
        def_end = def_start + timedelta(hours=1)
        defaults = {
            # from IDirectoryItem
            # description not used
            'title': '',

            # from IEventsDirectoryItem
            # submitter, submitter_email not used
            'short_description': '',
            'long_description': '',
            'image': '',
            'attachment_1': '',
            'attachment_2': '',
            'locality': '',
            'street': '',
            'housenumber': '',
            'zipcode': '',
            'town': '',
            'location_url': '',
            'event_url': '',
            'organizer': '',
            'contact_name': '',
            'contact_email': '',
            'contact_phone': '',
            'prices': '',
            'registration': '',

            # from IExternalEvent
            # source not used (filled in by ExternalEventImporter)
            'source_id': 'id-1',

            # From IEventBasic
            'start': def_start,
            'end': def_end,
            'whole_day': False,
            'timezone': default_timezone(),

            # From IEventRecurrence
            'recurrence': '',

            # additional attributes used to control import
            'fetch_id': 'fetch-1',
            'last_update': default_now().replace(microsecond=0),
            'latitude': '',
            'longitude': '',
            'cat1': set(),
            'cat2': set(),
        }

        for attr in defaults:
            if attr not in kw:
                kw[attr] = defaults[attr]

        return kw

    def addGuidleSource(self, title='Guidle Source', limit=25):
        browser = self.admin_browser

        # Add form
        browser.open('/veranstaltungen/++add++seantis.dir.events.sourceguidle')
        browser.widget('title').value = title
        browser.widget('url').value = 'http://localhost:8888/'
        browser.getControl('Enabled').selected = True
        browser.widget('limit').value = str(limit)

        # Save
        browser.getControl('Save').click()

        # Check if saved
        browser.open('/veranstaltungen/')
        self.assertTrue(title in browser.contents)

    @mock.patch('seantis.dir.events.sources.guidle.EventsSourceGuidle.fetch')
    def test_browser_import_guidle(self, fetch):
        anom = self.new_browser()
        admin = self.admin_browser

        self.addGuidleSource(title='GS1')
        self.addGuidleSource(title='GS2')
        self.addGuidleSource(title='GS3', limit=1)

        # Import events (two for each source)
        fetch.return_value = [
            self.create_fetch_entry(title='event1', source_id='event1'),
            self.create_fetch_entry(title='event2', source_id='event2')
        ]
        anom.open('/veranstaltungen/fetch?run=1&no_shuffle=True')

        # Anonymous users can't see import filters and sources
        anom.open('/veranstaltungen/')
        self.assertTrue('GS1' not in anom.contents)
        self.assertTrue('GS2' not in anom.contents)
        self.assertTrue('GS3' not in anom.contents)

        # Admins can see filters and sources
        admin.open('/veranstaltungen/')
        self.assertTrue('GS1' in admin.contents)
        self.assertTrue('GS2' in admin.contents)
        self.assertTrue('GS3' in admin.contents)
        self.assertTrue('/gs1' in admin.contents)
        self.assertTrue('/gs2' in admin.contents)
        self.assertTrue('/gs3' in admin.contents)

        # Filters
        admin.open('/veranstaltungen?source=gs1')
        self.assertTrue('/event1' in admin.contents)
        self.assertTrue('/event1-1' not in admin.contents)
        self.assertTrue('/event1-2' not in admin.contents)
        admin.open('/veranstaltungen?source=gs2')
        self.assertTrue('/event2-1' in admin.contents)
        self.assertTrue('/event2-2' not in admin.contents)

        # Limit
        admin.open('/veranstaltungen?source=gs3')
        self.assertTrue('/event1-2' in admin.contents)
        self.assertTrue('/event2-2' not in admin.contents)

        # Imported Events can be hidden
        admin.open('/veranstaltungen?source=')
        self.assertTrue('action=hide' in admin.contents)
        self.assertTrue('action=archive' not in admin.contents)

        # Hide an event
        admin.open('/veranstaltungen/event1-2/do-action?action=hide')
        admin.open('/veranstaltungen')
        self.assertTrue('/event1-2' not in admin.contents)
        admin.open('/veranstaltungen?state=hidden')
        self.assertTrue('action=publish' in admin.contents)
        self.assertTrue('/event1-2' in admin.contents)

        # Re-publish it
        admin.open('/veranstaltungen/event1-2/do-action?action=publish')
        admin.open('/veranstaltungen?state=published')
        self.assertTrue('/event1-2' in admin.contents)

        # Imported events may not be edited
        admin.open('/veranstaltungen/event2/edit')
        self.assertTrue('/gs1' in admin.contents)
        self.assertTrue('Title' not in admin.contents)
        self.assertTrue('Description' not in admin.contents)
        self.assertTrue('Save Event' not in admin.contents)

        # Imported events are not exported
        anom.open('/veranstaltungen?type=json')
        self.assertTrue('event1' not in anom.contents)

        # ... unless we request it!
        anom.open('/veranstaltungen?type=json&imported=1')
        self.assertTrue('event1' in anom.contents)

    def addSourceContentRule(self, title='rule', source=''):
        browser = self.admin_browser

        # Add rule
        browser.open('/+rule/plone.ContentRule')
        browser.getControl('Title').value = title
        browser.getControl('Object added to this container').selected = True
        browser.getControl('Save').click()

        # Add rule condition
        self.assertTrue('Event Import Source' in browser.contents)
        browser.getControl('Event Import Source').selected = True
        browser.getControl(name='form.button.AddCondition').click()
        self.assertTrue('The source id to check for.' in browser.contents)
        browser.getControl(name='form.source').value = source
        browser.getControl('Save').click()

        # Add rule action
        message = 'message_' + title + '_' + source
        browser.getControl('Notify user').selected = True
        browser.getControl(name='form.button.AddAction').click()
        browser.getControl(name='form.message').value = message
        browser.getControl('Save').click()

        # Assign rule
        browser.getControl('Apply rule on the whole site').click()

        # Check if saved
        browser.open('/@@rules-controlpanel')
        self.assertTrue(title in browser.contents)

    @mock.patch('seantis.dir.events.sources.guidle.EventsSourceGuidle.fetch')
    def test_browser_import_content_rule(self, fetch):
        browser = self.admin_browser

        # Add first guidle source
        self.addGuidleSource(title='gs1')

        # Add rules
        self.addSourceContentRule(title='all')
        self.addSourceContentRule(title='gs2', source='gs2')

        # Import events (one for each source)
        fetch.return_value = [
            self.create_fetch_entry(title='event'),
        ]
        browser.open('/veranstaltungen/fetch?run=1&force=true&no_shuffle=True')
        browser.open('/veranstaltungen')
        self.assertTrue('message_all_' in browser.contents)
        self.assertTrue('message_gs2_' not in browser.contents)

        # Add second guidle source
        self.addGuidleSource(title='gs2')
        browser.open('/veranstaltungen/fetch?run=1&force=true&no_shuffle=True')
        browser.open('/veranstaltungen')
        self.assertTrue('message_all_' in browser.contents)
        self.assertTrue('message_gs2_' in browser.contents)
