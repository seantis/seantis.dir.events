import mock
import pytz
import transaction

from collective.geo.geographer.interfaces import IGeoreferenced
from datetime import datetime, timedelta
from plone.app.event.base import default_timezone
from plone.dexterity.utils import createContentInContainer
from seantis.dir.events.catalog import reindex_directory
from seantis.dir.events.dates import default_now
from seantis.dir.events.sources import ExternalEventImporter, IExternalEvent
from seantis.dir.events.sources.guidle import EventsSourceGuidle
from seantis.dir.events.sources.seantis_json import EventsSourceSeantisJson
from seantis.dir.events.sources.ical import EventsSourceIcal

from seantis.dir.events.tests import IntegrationTestCase
from zope.interface import alsoProvides


GUIDLE_TEST_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<guidle:exportData xmlns:guidle="http://www.guidle.com">
<guidle:groupSet>
<guidle:group>
<guidle:offer id="123">
<guidle:lastUpdateDate>
  2013-07-26T16:00:43.208+02:00
</guidle:lastUpdateDate>
<guidle:offerDetail>
  <guidle:title>Title</guidle:title>
  <guidle:shortDescription>Description</guidle:shortDescription>
  <guidle:longDescription>Long Descritption</guidle:longDescription>
  <guidle:homepage>http://www.example.ch</guidle:homepage>
  <guidle:images>
    <guidle:image>
      <guidle:url>http://www.example.ch/1.png</guidle:url>
    </guidle:image>
  </guidle:images>
</guidle:offerDetail>
<guidle:address>
  <guidle:company>Address</guidle:company>
  <guidle:zip>1234</guidle:zip>
  <guidle:city>City</guidle:city>
  <guidle:country>Country</guidle:country>
  <guidle:latitude>1.0</guidle:latitude>
  <guidle:longitude>2.0</guidle:longitude>
</guidle:address>
<guidle:contact>
  <guidle:email>info@example.ch</guidle:email>
  <guidle:telephone_1>000 111 22 33</guidle:telephone_1>
  <guidle:company>Company</guidle:company>
</guidle:contact>
<guidle:schedules>
  <guidle:date>
    <guidle:startDate>2017-08-25</guidle:startDate>
    <guidle:endDate>2017-09-03</guidle:endDate>
    <guidle:weekdays>
      <guidle:day>Mo</guidle:day>
      <guidle:day>Tu</guidle:day>
    </guidle:weekdays>
  </guidle:date>
</guidle:schedules>
<guidle:classifications>
  <guidle:classification name="class">
  </guidle:classification>
</guidle:classifications>
</guidle:offer>
<guidle:offer id="234">
<guidle:lastUpdateDate>
  2013-07-26T16:00:43.208+02:00
</guidle:lastUpdateDate>
<guidle:offerDetail>
  <guidle:title>Title</guidle:title>
  <guidle:shortDescription>Description</guidle:shortDescription>
  <guidle:longDescription>Long Descritption</guidle:longDescription>
  <guidle:homepage>http://www.example.ch</guidle:homepage>
  <guidle:images>
    <guidle:image>
      <guidle:url>http://www.example.ch/1.png</guidle:url>
    </guidle:image>
  </guidle:images>
</guidle:offerDetail>
<guidle:address>
  <guidle:company>Address</guidle:company>
  <guidle:zip>1234</guidle:zip>
  <guidle:city>City</guidle:city>
  <guidle:country>Country</guidle:country>
</guidle:address>
<guidle:contact>
  <guidle:email>info@example.ch</guidle:email>
  <guidle:telephone_1>000 111 22 33</guidle:telephone_1>
  <guidle:company>Company</guidle:company>
</guidle:contact>
<guidle:schedules>
  <guidle:date>
    <guidle:startDate>2017-08-25</guidle:startDate>
    <guidle:endDate>2017-08-25</guidle:endDate>
    <guidle:startTime>09:15:00</guidle:startTime>
    <guidle:endTime>20:50:00</guidle:endTime>
  </guidle:date>
</guidle:schedules>
<guidle:classifications>
  <guidle:classification name="class">
  </guidle:classification>
</guidle:classifications>
</guidle:offer>
<guidle:offer id="50_1">
<guidle:lastUpdateDate>
  2014-05-28T11:20:35.736+02:00
</guidle:lastUpdateDate>
<guidle:offerDetail id="345">
  <guidle:title>Issue 50</guidle:title>
</guidle:offerDetail>
<guidle:address>
  <guidle:city>City</guidle:city>
</guidle:address>
<guidle:contact></guidle:contact>
<guidle:schedules>
  <guidle:date>
    <guidle:startDate>2014-03-12</guidle:startDate>
    <guidle:endDate>2014-12-31</guidle:endDate>
    <guidle:startTime>00:00:00</guidle:startTime>
    <guidle:endTime>00:00:00</guidle:endTime>
  </guidle:date>
</guidle:schedules>
<guidle:classifications>
  <guidle:classification name="class">
  </guidle:classification>
</guidle:classifications>
</guidle:offer>
<guidle:offer id="50_2">
<guidle:lastUpdateDate>
  2014-05-28T11:20:35.736+02:00
</guidle:lastUpdateDate>
<guidle:offerDetail id="345">
  <guidle:title>Issue 50 (2)</guidle:title>
</guidle:offerDetail>
<guidle:address>
  <guidle:city>City</guidle:city>
</guidle:address>
<guidle:contact></guidle:contact>
<guidle:schedules>
  <guidle:date>
    <guidle:startDate>2014-01-01</guidle:startDate>
    <guidle:endDate>2014-02-14</guidle:endDate>
    <guidle:startTime>07:00:00</guidle:startTime>
    <guidle:endTime>19:00:00</guidle:endTime>
  </guidle:date>
</guidle:schedules>
<guidle:classifications>
  <guidle:classification name="class">
  </guidle:classification>
</guidle:classifications>
</guidle:offer>
</guidle:group>
</guidle:groupSet>
</guidle:exportData>"""


class TestImport(IntegrationTestCase):

    def setUp(self):
        super(TestImport, self).setUp()
        # login to gain the right to create events
        self.login_admin()

    def tearDown(self):
        super(TestImport, self).tearDown()
        self.logout()

    def create_guidle_source(self, **kw):
        """ Create a guididle source item in self.directory.
        By default, test-user must
        be logged in or the creation will be unauthorized.

        """

        defaults = {
            'source': '',
            'enabled': True
        }

        for attr in defaults:
            if attr not in kw:
                kw[attr] = defaults[attr]

        return createContentInContainer(
            self.directory, 'seantis.dir.events.sourceguidle', **kw
        )

    def cleanup_after_fetch_one(self):
        """ fetch_one does a transaction.commit which causes the test folder
        and imported events to be persistent.
        """
        self.directory.manage_delObjects(self.directory.keys())
        self.portal.manage_delObjects([self.directory.id])
        transaction.commit()

    def create_fetch_entry(self, **kw):
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
            'start': datetime.today() + timedelta(days=10),
            'end': datetime.today() + timedelta(days=10, hours=1),
            'whole_day': False,
            'timezone': default_timezone(),

            # From IEventRecurrence
            'recurrence': '',

            # additional attributes used to control import
            'fetch_id': 'fetch-1',
            'last_update': default_now().replace(microsecond=0),
            # 'latitude': '',
            # 'longitude': '',
            'cat1': set(),
            'cat2': set(),
        }

        for attr in defaults:
            if attr not in kw:
                kw[attr] = defaults[attr]

        return kw

    def test_importer_sources(self):
        self.create_guidle_source(enabled=True)
        self.create_guidle_source(enabled=False)

        self.assertEqual(
            len(ExternalEventImporter(self.directory).sources()), 1)

    def test_importer_switch_indexing(self):
        importer = ExternalEventImporter(self.directory)

        event = self.create_event()
        event.submit()
        event.publish()
        reindex_directory(self.directory)
        self.assertEquals(len(self.catalog.ix_published.index), 1)

        importer.disable_indexing()
        event = self.create_event()
        event.submit()
        event.publish()
        reindex_directory(self.directory)
        self.assertEquals(len(self.catalog.ix_published.index), 1)

        importer.enable_indexing()
        reindex_directory(self.directory)
        self.assertEquals(len(self.catalog.ix_published.index), 2)

    def test_importer_update_time(self):
        importer = ExternalEventImporter(self.directory)

        set_time = lambda t: importer.set_last_update_time(t)
        get_time = lambda: importer.get_last_update_time()

        # No key
        self.assertRaises(AttributeError, get_time)
        self.assertRaises(AttributeError, set_time, default_now())
        self.assertRaises(AttributeError, get_time)

        importer.annotation_key = 'key'

        # Wrong dates
        self.assertRaises(AssertionError, set_time, None)
        self.assertRaises(AssertionError, set_time, 25)
        self.assertRaises(AssertionError, set_time, datetime.today())

        # Ok
        update = default_now()
        importer.set_last_update_time(update)
        last_update = importer.get_last_update_time()
        self.assertEquals(last_update, update.replace(microsecond=0))

    def test_importer_existing_events(self):
        importer = ExternalEventImporter(self.directory)

        sources = [('s1', 'id1'), ('s2', 'id1'), ('s1', 'id1'), ('s2', 'id2'),
                   ('', 'id2'), (None, 'id1'), ('s1', ''), ('s2', None)]

        for source in sources:
            args = {}
            if source[0] is not None:
                args = {
                    'source': source[0],
                    'source_id': source[1]
                }
            event = self.create_event(**args)
            event.submit()
            event.publish()
            if source is not None:
                alsoProvides(event, IExternalEvent)
            event.reindexObject()

        self.assertEquals(importer.grouped_existing_events(None), {})
        self.assertEquals(importer.grouped_existing_events(''), {})
        self.assertEquals(len(importer.grouped_existing_events('s1')), 1)
        self.assertEquals(
            len(importer.grouped_existing_events('s1')['id1']), 2
        )
        self.assertEquals(len(importer.grouped_existing_events('s2')), 2)
        self.assertEquals(
            len(importer.grouped_existing_events('s2')['id1']), 1
        )
        self.assertEquals(
            len(importer.grouped_existing_events('s2')['id2']), 1
        )
        self.assertEquals(importer.grouped_existing_events('s3'), {})

    def test_importer_fetch_one(self):
        try:
            importer = ExternalEventImporter(self.directory)
            events = []
            fetch = lambda: events
            from_ids = lambda ids: [self.create_fetch_entry(source_id=id,
                                                            fetch_id='f')
                                    for id in ids]

            # Simple import
            ids = ['event1', 'event2', 'event3', 'event4',
                   'event5', 'event6', 'event7', 'event8']
            events = from_ids(ids[:4])
            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 4)
            imported = [i.getObject().source_id for i in self.catalog.query()]
            self.assertEquals(ids[:4], imported)

            # Import with limit
            events = from_ids(ids[4:])
            imports, deleted = importer.fetch_one('source', fetch, limit=2)
            self.assertEquals(imports, 2)
            self.assertEquals(len(self.catalog.query()), 6)
            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 2)
            self.assertEquals(len(self.catalog.query()), 8)

            # Force reimport
            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 0)
            self.assertEquals(len(self.catalog.query()), 8)
            imports, deleted = importer.fetch_one('source', fetch,
                                                  reimport=True)
            self.assertEquals(imports, 4)
            self.assertEquals(len(self.catalog.query()), 8)

            # Reimport updated events
            events = from_ids(ids)
            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 8)
            self.assertEquals(len(self.catalog.query()), 8)

            # Test import of given source IDs only
            events = from_ids(ids)
            imports, deleted = importer.fetch_one(
                'source', fetch, source_ids=ids[2:6]
            )
            self.assertEquals(imports, 4)
            self.assertEquals(len(self.catalog.query()), 8)

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_importer_update_category_suggestions(self):
        try:
            importer = ExternalEventImporter(self.directory)

            events = []
            fetch = lambda: events

            events.append(self.create_fetch_entry(
                source_id='1', fetch_id='1',
                cat1=set(['cat1-1']), cat2=set(['cat2-1'])
            ))
            events.append(self.create_fetch_entry(
                source_id='2', fetch_id='1',
                cat1=set(['cat1-2', 'cat1-4']), cat2=set(['cat2-1'])
            ))
            events.append(self.create_fetch_entry(
                source_id='3', fetch_id='1',
                cat1=set(), cat2=set(['cat2-1', 'cat2-2', 'cat2-3'])
            ))

            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 3)
            self.assertTrue('cat1-1' in self.directory.cat1_suggestions)
            self.assertTrue('cat1-2' in self.directory.cat1_suggestions)
            self.assertTrue('cat1-4' in self.directory.cat1_suggestions)
            self.assertTrue('cat2-1' in self.directory.cat2_suggestions)
            self.assertTrue('cat2-2' in self.directory.cat2_suggestions)
            self.assertTrue('cat2-3' in self.directory.cat2_suggestions)

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_importer_values(self):
        try:
            importer = ExternalEventImporter(self.directory)

            string_values = [
                'title', 'short_description', 'long_description',
                'locality', 'street', 'housenumber', 'zipcode', 'town',
                'location_url', 'event_url', 'organizer',
                'contact_name', 'contact_email', 'contact_phone',
                'prices', 'registration',
                'source_id', 'fetch_id'
            ]
            now = default_now().replace(
                year=2015, month=1, day=1, microsecond=0
            )
            then = now + timedelta(days=10)

            event = {s: s for s in string_values}

            event['last_update'] = now
            event['start'] = then
            event['end'] = then + timedelta(hours=1)
            event['timezone'] = default_timezone()
            event['whole_day'] = False
            event['recurrence'] = 'RRULE:FREQ=DAILY;COUNT=2'

            event['cat1'] = set(['c1', 'c2'])
            event['cat2'] = set(['c3', 'c4'])

            event['longitude'] = 7.8673189
            event['latitude'] = 46.6859853

            # :TODO: test image and attachement download
            # event['image'] =
            # event['attachment_1'] =
            # event['attachment_2'] =

            imports, deleted = importer.fetch_one('source', lambda: [event])
            imported = self.catalog.query()
            self.assertEquals(imports, 1)
            self.assertEquals(len(imported), 1)

            imported = imported[0].getObject()
            for s in string_values:
                self.assertTrue(s in vars(imported))
                self.assertTrue(vars(imported)[s] == s)

            self.assertEquals(imported.start, now + timedelta(days=10))
            self.assertEquals(imported.end, now + timedelta(days=10, hours=1))
            self.assertEquals(imported.recurrence, 'RRULE:FREQ=DAILY;COUNT=2')
            self.assertFalse(imported.whole_day)

            self.assertTrue('c1' in imported.cat1)
            self.assertTrue('c2' in imported.cat1)
            self.assertTrue('c3' in imported.cat2)
            self.assertTrue('c4' in imported.cat2)

            self.assertEquals(
                IGeoreferenced(imported).coordinates, [7.8673189, 46.6859853]
            )

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_importer_autoremove(self):
        try:
            importer = ExternalEventImporter(self.directory)

            events = []
            fetch = lambda: events

            # First import
            events.append(self.create_fetch_entry(source_id='source_id_1',
                                                  fetch_id='fetch_id'))
            events.append(self.create_fetch_entry(source_id='source_id_1',
                                                  fetch_id='fetch_id'))
            events.append(self.create_fetch_entry(source_id='source_id_2',
                                                  fetch_id='fetch_id'))
            imports, deleted = importer.fetch_one('source', fetch)
            self.assertEquals(imports, 3)
            self.assertEquals(deleted, 0)
            self.assertEquals(len(self.directory.keys()), 3)

            # Second import
            events.pop(0)
            events.pop(0)
            events.append(self.create_fetch_entry(source_id='source_id_3',
                                                  fetch_id='fetch_id'))

            imports, deleted = importer.fetch_one('source', fetch,
                                                  autoremove=True)
            self.assertEquals(imports, 1)
            self.assertEquals(deleted, 2)

            ids = [item.source_id for id, item in self.directory.objectItems()]
            self.assertEquals(len(ids), 2)
            self.assertTrue('source_id_1' not in ids)

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_importer_keep_hidden(self):
        try:
            # Import event
            importer = ExternalEventImporter(self.directory)
            event = self.create_fetch_entry(source_id='s', fetch_id='f')
            imports, deleted = importer.fetch_one('source', lambda: [event])
            self.assertEquals(imports, 1)

            # Hide event
            brains = self.catalog.catalog(
                object_provides=IExternalEvent.__identifier__
            )
            self.assertEquals(len(brains), 1)
            hidden = brains[0].getObject()
            hidden.hide()

            # Re-import event
            imports, deleted = importer.fetch_one('source', lambda: [event])
            self.assertEquals(imports, 0)
            imports, deleted = importer.fetch_one(
                'source', lambda: [event], reimport=True
            )
            self.assertEquals(imports, 1)

            brains = self.catalog.catalog(
                object_provides=IExternalEvent.__identifier__
            )
            self.assertEquals(len(brains), 1)
            event = brains[0].getObject()
            self.assertTrue(
                event.modification_date != hidden.modification_date
            )
            self.assertEquals(event.review_state, 'hidden')

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_importer_export_imported(self):
        try:
            # Import event
            importer = ExternalEventImporter(self.directory)
            event = self.create_fetch_entry(source_id='s', fetch_id='f')
            imports, deleted = importer.fetch_one('source', lambda: [event])
            self.assertEquals(imports, 1)

            # Add own event
            event = self.create_event(start=datetime.today().replace(second=0))
            event.submit()
            event.publish()
            reindex_directory(self.directory)

            # Export events
            events = [idx for idx in enumerate(self.catalog.export())]
            self.assertEquals(len(events), 1)

        finally:
            # Clean up (transaction has been commited)
            self.cleanup_after_fetch_one()

    def test_guidle_import(self):
        xml = GUIDLE_TEST_DATA

        context = mock.Mock()
        context.url = 'url'

        source = EventsSourceGuidle(context)
        events = [event for event in source.fetch(xml)]
        self.assertEquals(len(events), 4)

        self.assertEquals(str(events[0]['last_update']),
                          '2013-07-26 16:00:43+02:00')
        self.assertEquals(events[0]['fetch_id'], 'url')
        self.assertEquals(events[0]['id'], '123')
        self.assertEquals(events[0]['source_id'], '123')
        self.assertEquals(events[0]['title'], 'Title')
        self.assertEquals(events[0]['short_description'], 'Description')
        self.assertEquals(events[0]['long_description'], 'Long Descritption')
        self.assertEquals(events[0]['location_url'], 'http://www.example.ch')
        self.assertEquals(events[0]['image'], 'http://www.example.ch/1.png')
        self.assertEquals(events[0]['organizer'], 'Company')
        self.assertEquals(events[0]['locality'], 'Address')
        self.assertEquals(events[0]['zipcode'], '1234')
        self.assertEquals(events[0]['town'], 'City')
        self.assertEquals(events[0]['contact_email'], 'info@example.ch')
        self.assertEquals(events[0]['contact_phone'], '000 111 22 33')
        self.assertEquals(events[0]['latitude'], '1.0')
        self.assertEquals(events[0]['longitude'], '2.0')
        self.assertEquals(events[0]['start'], datetime(2017, 8, 25, 0, 0))
        self.assertEquals(events[0]['end'], datetime(2017, 8, 25, 0, 0))
        self.assertEquals(events[0]['recurrence'],
                          'RRULE:FREQ=WEEKLY;BYDAY=MO,TU;UNTIL=20170904T0000Z')
        self.assertEquals(events[0]['whole_day'], True)
        self.assertEquals(events[0]['timezone'], 'Europe/Zurich')
        self.assertEquals(events[0]['cat1'], set())
        self.assertEquals(events[0]['cat2'], set(['City']))

        self.assertEquals(str(events[1]['last_update']),
                          '2013-07-26 16:00:43+02:00')
        self.assertEquals(events[1]['fetch_id'], 'url')
        self.assertEquals(events[1]['id'], '234')
        self.assertEquals(events[1]['source_id'], '234')
        self.assertEquals(events[1]['title'], 'Title')
        self.assertEquals(events[1]['short_description'], 'Description')
        self.assertEquals(events[1]['long_description'], 'Long Descritption')
        self.assertEquals(events[1]['location_url'], 'http://www.example.ch')
        self.assertEquals(events[1]['image'], 'http://www.example.ch/1.png')
        self.assertEquals(events[1]['organizer'], 'Company')
        self.assertEquals(events[1]['locality'], 'Address')
        self.assertEquals(events[1]['zipcode'], '1234')
        self.assertEquals(events[1]['town'], 'City')
        self.assertEquals(events[1]['contact_email'], 'info@example.ch')
        self.assertEquals(events[1]['contact_phone'], '000 111 22 33')
        self.assertTrue('latitude' not in events[1])
        self.assertTrue('longitude' not in events[1])
        self.assertEquals(events[1]['start'], datetime(2017, 8, 25, 9, 15))
        self.assertEquals(events[1]['end'], datetime(2017, 8, 25, 20, 50))
        self.assertEquals(events[1]['recurrence'], '')
        self.assertEquals(events[1]['whole_day'], False)
        self.assertEquals(events[1]['timezone'], 'Europe/Zurich')
        self.assertEquals(events[1]['cat1'], set())
        self.assertEquals(events[1]['cat2'], set(['City']))

        self.assertEquals(events[2]['start'], datetime(2014, 3, 12, 0, 0))
        self.assertEquals(events[2]['end'], datetime(2014, 3, 12, 0, 0))
        self.assertEquals(events[2]['recurrence'],
                          'RRULE:FREQ=DAILY;UNTIL=20150101T0000Z')
        self.assertEquals(events[2]['whole_day'], True)

        self.assertEquals(events[3]['start'], datetime(2014, 1, 1, 7, 0))
        self.assertEquals(events[3]['end'], datetime(2014, 1, 1, 19, 0))
        self.assertEquals(events[3]['recurrence'],
                          'RRULE:FREQ=DAILY;UNTIL=20140215T0000Z')
        self.assertEquals(events[3]['whole_day'], False)

    def test_seantis_import(self):
        json_string = """[{
            "id": "id1", "title": "title",
            "short_description": "short_description",
            "long_description": "h\u00e4nsel",
            "cat1": ["cat12", "cat11"], "cat2": ["cat21"],
            "event_url": "http://www.event.ch",
            "timezone": "Europe/Zurich",
            "start": "2014-01-15T00:00:00+00:00",
            "end": "2014-01-15T23:59:59+00:00",
            "whole_day": true,
            "recurrence": "RRULE:FREQ=WEEKLY;BYDAY=MO,TU;UNTIL=20150101T0000Z",
            "locality": "locality",
            "street": "street", "housenumber": "housenumber",
            "zipcode": "1234", "town": "town",
            "longitude": 2.0, "latitude": 1.0,
            "location_url": "http://www.location.ch",
            "contact_name": "contact_name",
            "contact_phone": "+12 (3) 45 678 90 12",
            "contact_email": "contact@ema.il",
            "registration": "http://www.tickets.ch",
            "organizer": "organizer",
            "prices": "prices",
            "images": [{"url": "img_url", "name": "img_name"}],
            "attachements": [
                {"url": "a1_url", "name": "a1_name"},
                {"url": "a2_url", "name": "a2_name"}
            ],
            "submitter": "sumitter", "submitter_email": "submitter@ma.il"
        },{
            "last_update": "2014-01-21T10:21:47+01:00",
            "id": "test", "title": "test",
            "short_description": "test", "long_description": null,
            "cat1": ["cat13", "cat14"], "cat2": ["cat21", "cat22", "cat23"],
            "event_url": null,
            "timezone": "UTC",
            "start": "2014-01-19T17:00:00+02:00",
            "end": "2014-01-19T18:00:00+02:00",
            "whole_day": false, "recurrence": null,
            "locality": null, "street": null, "housenumber": null,
            "zipcode": null, "town": null,
            "longitude": null, "latitude": null,
            "location_url": null,
            "contact_name": null, "contact_phone": null, "contact_email": null,
            "registration": null, "organizer": null, "prices": null,
            "images": null, "attachments": [],
            "submitter": "cccc", "submitter_email": "submitter@ma.il"
        }]"""

        context = mock.Mock()
        context.url = 'url'
        context.do_filter = False
        context.cat1 = ''
        context.cat2 = ''

        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 2)

        self.assertTrue(
            default_now() - events[0]['last_update'] < timedelta(seconds=10)
        )
        self.assertEquals(events[0]['fetch_id'], 'url')
        self.assertEquals(events[0]['id'], 'id1')
        self.assertEquals(events[0]['source_id'], 'id1')
        self.assertEquals(events[0]['title'], 'title')
        self.assertEquals(events[0]['short_description'], u'short_description')
        self.assertEquals(events[0]['long_description'], u'h\xe4nsel')
        self.assertEquals(events[0]['event_url'], 'http://www.event.ch')
        self.assertEquals(events[0]['registration'], 'http://www.tickets.ch')
        self.assertEquals(events[0]['location_url'], 'http://www.location.ch')
        self.assertEquals(events[0]['image'], 'img_url')
        self.assertEquals(events[0]['image_name'], 'img_name')
        self.assertEquals(events[0]['attachment_1'], 'a1_url')
        self.assertEquals(events[0]['attachment_1_name'], 'a1_name')
        self.assertEquals(events[0]['attachment_2'], 'a2_url')
        self.assertEquals(events[0]['attachment_2_name'], 'a2_name')
        self.assertEquals(events[0]['organizer'], 'organizer')
        self.assertEquals(events[0]['street'], 'street')
        self.assertEquals(events[0]['housenumber'], 'housenumber')
        self.assertEquals(events[0]['locality'], 'locality')
        self.assertEquals(events[0]['zipcode'], '1234')
        self.assertEquals(events[0]['town'], 'town')
        self.assertEquals(events[0]['contact_name'], 'contact_name')
        self.assertEquals(events[0]['contact_email'], 'contact@ema.il')
        self.assertEquals(events[0]['contact_phone'], '+12 (3) 45 678 90 12')
        self.assertEquals(events[0]['latitude'], '1.0')
        self.assertEquals(events[0]['longitude'], '2.0')
        self.assertEquals(events[0]['timezone'], 'Europe/Zurich')
        self.assertEquals(events[0]['start'], datetime(2014, 1, 15, 0, 0,
                                                       tzinfo=pytz.UTC))
        self.assertEquals(events[0]['end'], datetime(2014, 1, 15, 23, 59, 59,
                                                     tzinfo=pytz.UTC))
        self.assertEquals(events[0]['recurrence'],
                          'RRULE:FREQ=WEEKLY;BYDAY=MO,TU;UNTIL=20150101T0000Z')
        self.assertEquals(events[0]['whole_day'], True)
        self.assertEquals(events[0]['cat1'], set(['cat11', 'cat12']))
        self.assertEquals(events[0]['cat2'], set(['cat21']))
        self.assertEquals(events[0]['submitter'], 'sumitter')
        self.assertEquals(events[0]['submitter_email'], 'submitter@ma.il')

        self.assertEquals(
            events[1]['last_update'],
            datetime(2014, 1, 21, 9, 21, 47, tzinfo=pytz.UTC)
        )
        self.assertEquals(events[1]['latitude'], None)
        self.assertEquals(events[1]['longitude'], None)
        self.assertEquals(events[1]['timezone'], 'UTC')
        self.assertEquals(events[1]['start'], datetime(2014, 1, 19, 15, 0,
                                                       tzinfo=pytz.UTC))
        self.assertEquals(events[1]['end'], datetime(2014, 1, 19, 16, 0,
                                                     tzinfo=pytz.UTC))
        self.assertEquals(events[1]['whole_day'], False)
        self.assertEquals(events[1]['cat1'], set(['cat13', 'cat14']))
        self.assertEquals(events[1]['cat2'], set(['cat21', 'cat22', 'cat23']))

        # Filter by categories
        context.do_filter = False
        context.cat1 = 'cat5'
        context.cat2 = 'cat6'
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 2)

        context.do_filter = True

        context.cat1 = ''
        context.cat2 = ''
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 2)

        context.cat1 = 'cat1'
        context.cat2 = ''
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 0)

        context.cat1 = 'cat11'
        context.cat2 = ''
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0]['cat1'], set(['cat11', 'cat12']))

        context.cat1 = 'cat12'
        context.cat2 = ''
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0]['cat1'], set(['cat11', 'cat12']))

        context.cat1 = ''
        context.cat2 = 'cat23'
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0]['cat2'], set(['cat21', 'cat22', 'cat23']))

        context.cat1 = ''
        context.cat2 = 'cat24'
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 0)

        context.do_filter = True
        context.cat1 = 'cat11'
        context.cat2 = 'cat21'
        source = EventsSourceSeantisJson(context)
        events = [event for event in source.fetch(json_string)]
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0]['cat1'], set(['cat11', 'cat12']))
        self.assertEquals(events[0]['cat2'], set(['cat21']))

    def test_ical_import(self):
        ical_string = '\n'.join((
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//CodX Software AG//WinFAP TS 9.0',
            'METHOD:PUBLISH',
            'BEGIN:VTIMEZONE',
            'TZID:W. Europe Standard Time',
            'BEGIN:STANDARD',
            'DTSTART:16011028T030000',
            'TZOFFSETFROM:+0200',
            'TZOFFSETTO:+0100',
            'RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10',
            'END:STANDARD',
            'BEGIN:DAYLIGHT',
            'DTSTART:16010325T020000',
            'TZOFFSETFROM:+0100',
            'TZOFFSETTO:+0200',
            'RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3',
            'END:DAYLIGHT',
            'END:VTIMEZONE',
            'BEGIN:VEVENT',
            'UID:D9ED6A0B',
            'DTSTAMP:20151013T121911Z',
            'LAST-MODIFIED:20151013T121911Z',
            'DTSTART;TZID="W. Europe Standard Time":20161115T193000',
            'DURATION:PT2H0M0S',
            'SUMMARY;LANGUAGE=de:5. Uebung Fahrtraining C',
            'END:VEVENT',
            'BEGIN:VEVENT',
            'UID:7DF26883',
            'ORGANIZER:feuerwehr@steinhausen.ch',
            'DTSTAMP:20150928T134125Z',
            'LAST-MODIFIED:20150928T134125Z',
            'DTSTART;VALUE=DATE:20160402',
            'DTEND;VALUE=DATE:20160403',
            'SUMMARY;LANGUAGE=de:EFK Neueingeteilte im Verkehrsdienst',
            'LOCATION;LANGUAGE=de:FFZ, 6300 Zug',
            'DESCRIPTION;LANGUAGE=de:GVZG 1653',
            'END:VEVENT',
            'BEGIN:VEVENT',
            'UID:F2D33EA6',
            'ORGANIZER:feuerwehr@steinhausen.ch',
            'DTSTAMP:20150707T105252Z',
            'LAST-MODIFIED:20150707T105252Z',
            'DTSTART;VALUE=DATE:20161222',
            'DTEND;VALUE=DATE:20170105',
            'SUMMARY;LANGUAGE=de:Weihnachtsferien',
            'DESCRIPTION;LANGUAGE=de:GVZG 1601',
            'END:VEVENT',
            'END:VCALENDAR'
        ))

        context = mock.Mock()
        context.url = 'url'
        context.default_description = 'default'

        source = EventsSourceIcal(context)
        events = [event for event in source.fetch(ical_string)]

        self.assertEquals(len(events), 3)

        e = events[0]
        self.assertEquals(e['attachment_1'], None)
        self.assertEquals(e['attachment_2'], None)
        self.assertEquals(e['cat1'], set([]))
        self.assertEquals(e['cat2'], set([]))
        self.assertEquals(e['contact_email'], '')
        self.assertEquals(e['contact_name'], '')
        self.assertEquals(e['contact_phone'], '')
        self.assertEquals(e['end'], datetime(2016, 11, 15, 20, 30,
                                             tzinfo=pytz.UTC))
        self.assertEquals(e['event_url'], '')
        self.assertEquals(e['fetch_id'], 'url')
        self.assertEquals(e['housenumber'], '')
        self.assertEquals(e['image'], None)
        self.assertEquals(e['last_update'], datetime(2015, 10, 13, 12, 19, 11,
                                                     tzinfo=pytz.UTC))
        self.assertEquals(e['latitude'], None)
        self.assertEquals(e['locality'], '')
        self.assertEquals(e['location_url'], '')
        self.assertEquals(e['long_description'], '')
        self.assertEquals(e['longitude'], None)
        self.assertEquals(e['organizer'], '')
        self.assertEquals(e['prices'], '')
        self.assertEquals(e['recurrence'], '')
        self.assertEquals(e['registration'], '')
        self.assertEquals(e['short_description'], 'default')
        self.assertEquals(e['source_id'], u'D9ED6A0B')
        self.assertEquals(e['start'], datetime(2016, 11, 15, 18, 30,
                                               tzinfo=pytz.UTC))
        self.assertEquals(e['street'], '')
        self.assertEquals(e['submitter'], 'ical@example.com')
        self.assertEquals(e['submitter_email'], 'ical@example.com')
        self.assertEquals(e['timezone'], 'Europe/Zurich')
        self.assertEquals(e['title'], u'5. Uebung Fahrtraining C')
        self.assertEquals(e['town'], '')
        self.assertEquals(e['whole_day'], False)
        self.assertEquals(e['zipcode'], '')

        e = events[1]
        self.assertEquals(e['attachment_1'], None)
        self.assertEquals(e['attachment_2'], None)
        self.assertEquals(e['cat1'], set([]))
        self.assertEquals(e['cat2'], set([]))
        self.assertEquals(e['contact_email'], '')
        self.assertEquals(e['contact_name'], '')
        self.assertEquals(e['contact_phone'], '')
        self.assertEquals(e['end'], datetime(2016, 4, 2, 21, 59, 59, 999999,
                                             tzinfo=pytz.UTC))
        self.assertEquals(e['event_url'], '')
        self.assertEquals(e['fetch_id'], 'url')
        self.assertEquals(e['housenumber'], '')
        self.assertEquals(e['image'], None)
        self.assertEquals(e['last_update'], datetime(2015, 9, 28, 13, 41, 25,
                                                     tzinfo=pytz.UTC))
        self.assertEquals(e['latitude'], None)
        self.assertEquals(e['locality'], 'FFZ, 6300 Zug')
        self.assertEquals(e['location_url'], '')
        self.assertEquals(e['long_description'], '')
        self.assertEquals(e['longitude'], None)
        self.assertEquals(e['organizer'], '')
        self.assertEquals(e['prices'], '')
        self.assertEquals(e['recurrence'], '')
        self.assertEquals(e['registration'], '')
        self.assertEquals(e['short_description'], 'GVZG 1653')
        self.assertEquals(e['source_id'], u'7DF26883')
        self.assertEquals(e['start'], datetime(2016, 4, 1, 22, 0,
                                               tzinfo=pytz.UTC))
        self.assertEquals(e['street'], '')
        self.assertEquals(e['submitter'], 'feuerwehr@steinhausen.ch')
        self.assertEquals(e['submitter_email'], 'feuerwehr@steinhausen.ch')
        self.assertEquals(e['timezone'], 'Europe/Zurich')
        self.assertEquals(e['title'], u'EFK Neueingeteilte im Verkehrsdienst')
        self.assertEquals(e['town'], '')
        self.assertEquals(e['whole_day'], True)
        self.assertEquals(e['zipcode'], '')

        e = events[2]
        self.assertEquals(e['attachment_1'], None)
        self.assertEquals(e['attachment_2'], None)
        self.assertEquals(e['cat1'], set())
        self.assertEquals(e['cat2'], set())
        self.assertEquals(e['contact_email'], '')
        self.assertEquals(e['contact_name'], '')
        self.assertEquals(e['contact_phone'], '')
        self.assertEquals(e['end'], datetime(2017, 1, 4, 22, 59, 59, 999999,
                                             tzinfo=pytz.UTC))
        self.assertEquals(e['event_url'], '')
        self.assertEquals(e['fetch_id'], 'url')
        self.assertEquals(e['housenumber'], '')
        self.assertEquals(e['image'], None)
        self.assertEquals(e['last_update'], datetime(2015, 7, 7, 10, 52, 52,
                                                     tzinfo=pytz.UTC))
        self.assertEquals(e['latitude'], None)
        self.assertEquals(e['locality'], '')
        self.assertEquals(e['location_url'], '')
        self.assertEquals(e['long_description'], '')
        self.assertEquals(e['longitude'], None)
        self.assertEquals(e['organizer'], '')
        self.assertEquals(e['prices'], '')
        self.assertEquals(e['recurrence'], '')
        self.assertEquals(e['registration'], '')
        self.assertEquals(e['short_description'], u'GVZG 1601')
        self.assertEquals(e['source_id'], u'F2D33EA6')
        self.assertEquals(e['start'], datetime(2016, 12, 21, 23, 0,
                                               tzinfo=pytz.UTC))
        self.assertEquals(e['street'], '')
        self.assertEquals(e['submitter'], u'feuerwehr@steinhausen.ch')
        self.assertEquals(e['submitter_email'], u'feuerwehr@steinhausen.ch')
        self.assertEquals(e['timezone'], 'Europe/Zurich')
        self.assertEquals(e['title'], u'Weihnachtsferien')
        self.assertEquals(e['town'], '')
        self.assertEquals(e['whole_day'], True)
        self.assertEquals(e['zipcode'], '')

    def test_seantis_import_build_url(self):
        context = mock.Mock()
        context.url = '  http://www.ex.ch/ev/  '
        context.do_filter = False
        context.import_imported = False
        context.cat1 = ''
        context.cat2 = ''
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev/?type=json&compact=true'
        )

        context.url = '  http://www.ex.ch/ev  '
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true'
        )

        context.do_filter = True
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true'
        )

        context.cat1 = 'cat1'
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true&filter=true&cat1=cat1'
        )

        context.cat1 = ''
        context.cat2 = 'cat2'
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true&filter=true&cat2=cat2'
        )

        context.cat1 = 'cat1'
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true&filter=true'
            '&cat1=cat1&cat2=cat2'
        )

        context.import_imported = True
        source = EventsSourceSeantisJson(context)
        self.assertEquals(
            source.build_url(),
            'http://www.ex.ch/ev?type=json&compact=true&imported=1&filter=true'
            '&cat1=cat1&cat2=cat2'
        )
