from datetime import datetime, timedelta

from collective.geo.geographer.interfaces import IGeoreferenced
from plone.app.event.base import default_timezone
from plone.dexterity.utils import createContentInContainer
from zope.interface import alsoProvides

from seantis.dir.events.catalog import reindex_directory
from seantis.dir.events.dates import default_now
from seantis.dir.events.sources import (
    import_scheduler, ExternalEventImporter, IExternalEvent
)
from seantis.dir.events.sources.guidle import EventsSourceGuidle
from seantis.dir.events.tests import IntegrationTestCase

import transaction


class DummyGuidleContext():

    def __init__(self, url):
        self.url = url


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
            if not attr in kw:
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
            'latitude': '',
            'longitude': '',
            'cat1': set(),
            'cat2': set(),
        }

        for attr in defaults:
            if not attr in kw:
                kw[attr] = defaults[attr]

        return kw

    def test_import_scheduler_next_run(self):
        real_now = datetime.today()
        today = datetime(real_now.year, real_now.month, real_now.day)
        tomorrow = today + timedelta(days=1)

        # Test daily interval
        next_run = import_scheduler.get_next_run(now=today)
        self.assertEqual(next_run, today + timedelta(hours=2))

        now = today + timedelta(minutes=10)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, today + timedelta(hours=2))

        now = today + timedelta(hours=1, minutes=59)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, today + timedelta(hours=2))

        now = today + timedelta(hours=2)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, tomorrow + timedelta(hours=2))

        now = today + timedelta(hours=2, minutes=30)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, tomorrow + timedelta(hours=2))

        now = today + timedelta(hours=4)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, tomorrow + timedelta(hours=2))

        now = today + timedelta(hours=12)
        next_run = import_scheduler.get_next_run(now=now)
        self.assertEqual(next_run, tomorrow + timedelta(hours=2))

        # Test hourly interval
        now = today + timedelta(minutes=10)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, today + timedelta(hours=1))

        now = today + timedelta(minutes=40)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, today + timedelta(hours=1))

        now = today + timedelta(minutes=59)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, today + timedelta(hours=1))

        now = today + timedelta(hours=1, minutes=1)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, today + timedelta(hours=2))

        now = today + timedelta(hours=23, minutes=59)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, tomorrow)

        now = today + timedelta(days=3, hours=17, minutes=28)
        next_run = import_scheduler.get_next_run(interval='hourly', now=now)
        self.assertEqual(next_run, today + timedelta(days=3, hours=18))

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

        sources = 2 * ['source1', 'source1', 'source2', '', None, 'source-3']
        for source in sources:
            args = {} if source is None else {'source': source}
            event = self.create_event(**args)
            event.submit()
            event.publish()
            if source is not None:
                alsoProvides(event, IExternalEvent)
            event.reindexObject()

        for source in list(set(sources)):
            if source is not None:
                self.assertEquals(len(importer.existing_events(source)),
                                  sources.count(source))

    def test_importer_group_by_source_id(self):
        importer = ExternalEventImporter(self.directory)

        ids = ['1', '101', '27', '100', '2', '100', '27', '1']
        events = [self.create_event(source_id=id) for id in ids]

        groups = importer.groupby_source_id(events)
        for id in groups:
            self.assertEquals(len(groups[id]), ids.count(id))

    def test_importer_fetch_one(self):
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
        imports, runtime = importer.fetch_one('source', fetch)
        self.assertEquals(imports, 4)
        imported = [i.getObject().source_id for i in self.catalog.query()]
        self.assertEquals(ids[:4], imported)

        # Import with limit
        events = from_ids(ids[4:])
        imports, runtime = importer.fetch_one('source', fetch, limit=2)
        self.assertEquals(imports, 3)
        self.assertEquals(len(self.catalog.query()), 7)
        imports, runtime = importer.fetch_one('source', fetch)
        self.assertEquals(imports, 1)
        self.assertEquals(len(self.catalog.query()), 8)

        # Force reimport
        imports, runtime = importer.fetch_one('source', fetch)
        self.assertEquals(imports, 0)
        self.assertEquals(len(self.catalog.query()), 8)
        imports, runtime = importer.fetch_one('source', fetch, reimport=True)
        self.assertEquals(imports, 4)
        self.assertEquals(len(self.catalog.query()), 8)

        # Reimport updated events
        events = from_ids(ids)
        imports, runtime = importer.fetch_one('source', fetch)
        self.assertEquals(imports, 8)
        self.assertEquals(len(self.catalog.query()), 8)

        # Test import of given source IDs only
        events = from_ids(ids)
        imports, runtime = importer.fetch_one(
            'source', fetch, source_ids=ids[2:6]
        )
        self.assertEquals(imports, 4)
        self.assertEquals(len(self.catalog.query()), 8)

        # Clean up (transaction has been commited)
        self.cleanup_after_fetch_one()

    def test_importer_update_category_suggestions(self):
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

        imports, runtime = importer.fetch_one('source', fetch)
        self.assertEquals(imports, 3)
        self.assertTrue('cat1-1' in self.directory.cat1_suggestions)
        self.assertTrue('cat1-2' in self.directory.cat1_suggestions)
        self.assertTrue('cat1-4' in self.directory.cat1_suggestions)
        self.assertTrue('cat2-1' in self.directory.cat2_suggestions)
        self.assertTrue('cat2-2' in self.directory.cat2_suggestions)
        self.assertTrue('cat2-3' in self.directory.cat2_suggestions)

        # Clean up (transaction has been commited)
        self.cleanup_after_fetch_one()

    def test_importer_values(self):
        importer = ExternalEventImporter(self.directory)

        string_values = [
            'title', 'short_description', 'long_description',
            'locality', 'street', 'housenumber', 'zipcode', 'town',
            'location_url', 'event_url', 'organizer',
            'contact_name', 'contact_email', 'contact_phone',
            'prices', 'registration',
            'source_id', 'fetch_id'
        ]
        now = default_now().replace(microsecond=0)
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

        imports, runtime = importer.fetch_one('source', lambda: [event])
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

        self.assertEquals(IGeoreferenced(imported).coordinates,
                          [7.8673189, 46.6859853])

        # Clean up (transaction has been commited)
        self.cleanup_after_fetch_one()

    def test_importer_keep_hidden(self):
        # Import event
        importer = ExternalEventImporter(self.directory)
        event = self.create_fetch_entry(source_id='s', fetch_id='f')
        imports, runtime = importer.fetch_one('source', lambda: [event])
        self.assertEquals(imports, 1)

        # Hide event
        brains = self.catalog.catalog(
            object_provides=IExternalEvent.__identifier__
        )
        self.assertEquals(len(brains), 1)
        hidden = brains[0].getObject()
        hidden.hide()

        # Re-import event
        imports, runtime = importer.fetch_one('source', lambda: [event])
        self.assertEquals(imports, 0)
        imports, runtime = importer.fetch_one(
            'source', lambda: [event], reimport=True
        )
        self.assertEquals(imports, 1)

        brains = self.catalog.catalog(
            object_provides=IExternalEvent.__identifier__
        )
        self.assertEquals(len(brains), 1)
        event = brains[0].getObject()
        self.assertTrue(event.modification_date != hidden.modification_date)
        self.assertEquals(event.review_state, 'hidden')

        # Clean up (transaction has been commited)
        self.cleanup_after_fetch_one()

    def test_guidle_import(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<guidle:exportData xmlns:guidle="http://www.guidle.com">
  <guidle:groupSet>
    <guidle:group>
      <guidle:offer id="123">
        <guidle:lastUpdateDate>2013-07-26T16:00:43.208+02:00</guidle:lastUpdateDate>
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
        <guidle:lastUpdateDate>2013-07-26T16:00:43.208+02:00</guidle:lastUpdateDate>
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
    </guidle:group>
  </guidle:groupSet>
</guidle:exportData>"""

        context = DummyGuidleContext('url')
        source = EventsSourceGuidle(context)
        events = [event for event in source.fetch(xml)]
        self.assertEquals(len(events), 2)

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
        self.assertEquals(events[0]['cat1'], set(['class']))
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
        self.assertEquals(events[1]['cat1'], set(['class']))
        self.assertEquals(events[1]['cat2'], set(['City']))
