import os

from datetime import datetime, timedelta
from DateTime.DateTime import DateTime

from zope.interface import alsoProvides

from seantis.dir.events.cleanup import cleanup_scheduler
from seantis.dir.events.dates import to_utc
from seantis.dir.events.interfaces import IExternalEvent
from seantis.dir.events.tests import IntegrationTestCase


class TestCleanup(IntegrationTestCase):

    def setUp(self):
        super(TestCleanup, self).setUp()
        # login to gain the right to create events
        self.login_admin()

    def tearDown(self):
        super(TestCleanup, self).tearDown()
        self.logout()

    def test_remove_stale_previews(self):
        preview = self.create_event()
        self.assertEqual(preview.state, 'preview')

        run_dry = lambda: cleanup_scheduler.remove_stale_previews(
            self.directory, dryrun=True
        )
        run = lambda: cleanup_scheduler.remove_stale_previews(
            self.directory, dryrun=False
        )

        self.assertEqual(run(), [])

        # Age event
        preview.modification_date = DateTime(
            datetime.utcnow() - timedelta(days=2, microseconds=1)
        )
        preview.reindexObject(idxs=['modified'])

        # Test dryrun
        self.assertEqual(run_dry(), [preview.id])
        self.assertEqual(len(self.catalog.catalog()), 2)

        # Test run
        self.assertEqual(run(), [])
        self.assertEqual(len(self.catalog.catalog()), 1)

    def test_archive_past_events(self):

        run_dry = lambda: cleanup_scheduler.archive_past_events(
            self.directory, dryrun=True
        )
        run = lambda: cleanup_scheduler.archive_past_events(
            self.directory, dryrun=False
        )

        published = self.create_event()
        self.assertEqual(run(), [])

        published.submit()
        self.assertEqual(run(), [])

        published.publish()
        self.assertEqual(run(), [])

        # Age event
        published.start = to_utc(datetime.utcnow() - timedelta(days=3))
        published.end = to_utc(datetime.utcnow() - timedelta(days=3))
        published.reindexObject(idxs=['start', 'end'])

        # Test dryruns
        self.assertEqual(run_dry(), [published.id])

        published.start += timedelta(days=2)
        published.end += timedelta(days=2)
        published.reindexObject(idxs=['start', 'end'])
        self.assertEqual(run_dry(), [])

        published.start = to_utc(datetime.utcnow() - timedelta(days=3))
        published.end = to_utc(datetime.utcnow() - timedelta(days=3))
        published.reindexObject(idxs=['start', 'end'])
        self.assertEqual(run_dry(), [published.id])

        published.recurrence = 'RRULE:FREQ=WEEKLY;COUNT=10'
        self.assertEqual(run_dry(), [])

        published.start = to_utc(datetime.utcnow() - timedelta(days=100))
        published.end = to_utc(datetime.utcnow() - timedelta(days=100))
        published.recurrence = 'RRULE:FREQ=WEEKLY;COUNT=3'
        published.reindexObject(idxs=['start', 'end'])

        self.assertEqual(run_dry(), [published.id])

        # Test run
        self.assertEqual(run(), [published.id])
        self.assertEqual(published.state, 'archived')

    def test_remove_archived_events(self):

        run_dry = lambda: cleanup_scheduler.remove_archived_events(
            self.directory, dryrun=True
        )
        run = lambda: cleanup_scheduler.remove_archived_events(
            self.directory, dryrun=False
        )

        archived = self.create_event()
        self.assertEqual(run(), [])

        archived.submit()
        self.assertEqual(run(), [])

        archived.publish()
        self.assertEqual(run(), [])

        # Age event
        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])

        # Test dryruns
        self.assertEqual(run_dry(), [])

        archived.archive()
        self.assertEqual(run_dry(), [archived.id])

        archived.start = to_utc(datetime.utcnow() - timedelta(days=10))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=10))
        archived.reindexObject(idxs=['start', 'end'])

        self.assertEqual(run_dry(), [])

        # Test run
        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])

        self.assertEqual(len(self.catalog.catalog()), 2)
        self.assertEqual(run(), [])
        self.assertEqual(len(self.catalog.catalog()), 1)

    def test_keep_permanently_archived_events(self):

        run = lambda: cleanup_scheduler.remove_archived_events(
            self.directory, dryrun=False
        )

        archived = self.create_event()
        archived.submit()
        archived.publish()
        archived.archive()
        archived.archive_permanently()

        # Age event
        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])

        # Test run
        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])

        self.assertEqual(len(self.catalog.catalog()), 2)
        self.assertEqual(run(), [])
        self.assertEqual(len(self.catalog.catalog()), 2)

    def test_remove_past_imported_events(self):

        run_dry = lambda: cleanup_scheduler.remove_past_imported_events(
            self.directory, dryrun=True
        )
        run = lambda: cleanup_scheduler.remove_past_imported_events(
            self.directory, dryrun=False
        )

        imported = self.create_event()
        imported.submit()
        imported.publish()
        alsoProvides(imported, IExternalEvent)
        imported.reindexObject()
        self.assertEqual(run(), [])

        hidden = self.create_event()
        hidden.submit()
        hidden.publish()
        alsoProvides(hidden, IExternalEvent)
        hidden.hide()
        hidden.reindexObject()
        self.assertEqual(run(), [])

        # Age events
        imported.start = to_utc(datetime.utcnow() - timedelta(days=10))
        imported.end = to_utc(datetime.utcnow() - timedelta(days=10))
        imported.reindexObject(idxs=['start', 'end'])
        hidden.start = to_utc(datetime.utcnow() - timedelta(days=10))
        hidden.end = to_utc(datetime.utcnow() - timedelta(days=10))
        hidden.reindexObject(idxs=['start', 'end'])

        # Test dryruns
        ids = run_dry()
        self.assertEqual(len(ids), 2)
        self.assertTrue(imported.id in ids)
        self.assertTrue(hidden.id in ids)

        # Test run
        self.assertEqual(len(self.catalog.catalog()), 3)
        self.assertEqual(run(), [])
        self.assertEqual(len(self.catalog.catalog()), 1)

    def test_cleanup_directory(self):
        preview = self.create_event()
        preview.modification_date = DateTime(
            datetime.utcnow() - timedelta(days=2, microseconds=1)
        )
        preview.reindexObject(idxs=['modified'])

        published = self.create_event()
        published.submit()
        published.publish()
        published.start = to_utc(datetime.utcnow() - timedelta(days=3))
        published.end = to_utc(datetime.utcnow() - timedelta(days=3))
        published.reindexObject(idxs=['start', 'end'])

        archived = self.create_event()
        archived.submit()
        archived.publish()
        archived.archive()
        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])

        cleanup_scheduler.cleanup_directory(self.directory, dryrun=True)
        self.assertEqual(len(self.catalog.catalog()), 4)
        cleanup_scheduler.cleanup_directory(self.directory, dryrun=False)
        self.assertEqual(published.state, 'archived')
        self.assertEqual(len(self.catalog.catalog()), 2)

    def test_cleanup_scheduler_next_run(self):
        real_now = datetime.today()
        today = datetime(real_now.year, real_now.month, real_now.day)
        tomorrow = today + timedelta(days=1)

        next_run = cleanup_scheduler.get_next_run(today)
        self.assertEqual(next_run, today + timedelta(minutes=30))

        now = today + timedelta(minutes=10)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, today + timedelta(minutes=30))

        now = today + timedelta(minutes=29)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, today + timedelta(minutes=30))

        now = today + timedelta(minutes=30)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, tomorrow + timedelta(minutes=30))

        now = today + timedelta(hours=1, minutes=30)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, tomorrow + timedelta(minutes=30))

        now = today + timedelta(hours=4)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, tomorrow + timedelta(minutes=30))

        now = today + timedelta(hours=12)
        next_run = cleanup_scheduler.get_next_run(now)
        self.assertEqual(next_run, tomorrow + timedelta(minutes=30))

    def test_cleanup_scheduler_run(self):
        real_now = datetime.today()
        today = datetime(real_now.year, real_now.month, real_now.day)

        # Add stale event
        preview = self.create_event()
        preview.modification_date = DateTime(
            datetime.utcnow() - timedelta(days=20)
        )
        preview.reindexObject(idxs=['modified'])

        # No cleanup yet
        now = today + timedelta(hours=12)
        cleanup_scheduler.run(self.directory, now=now)
        now = today + timedelta(hours=13)
        cleanup_scheduler.run(self.directory, now=now)
        self.assertEqual(len(self.catalog.catalog()), 2)

        # Not importing instance
        now = today + timedelta(hours=14)
        cleanup_scheduler.run(self.directory, force_run=True, now=now)
        self.assertEqual(len(self.catalog.catalog()), 2)

        os.environ['seantis_events_cleanup'] = 'true'

        # Force cleanup now
        now = today + timedelta(hours=14)
        cleanup_scheduler.run(self.directory, force_run=True, now=now)
        self.assertEqual(len(self.catalog.catalog()), 1)

        # Dryrun
        preview = self.create_event()
        preview.modification_date = DateTime(
            datetime.utcnow() - timedelta(days=20)
        )
        preview.reindexObject(idxs=['modified'])

        now = today + timedelta(days=1, hours=8)
        cleanup_scheduler.run(self.directory, dryrun=True, now=now)
        now = today + timedelta(days=1, hours=8)
        cleanup_scheduler.run(self.directory, dryrun=True, force_run=True,
                              now=now)
        self.assertEqual(len(self.catalog.catalog()), 2)

        # Normal cleanup
        now = today + timedelta(days=2, hours=8)
        cleanup_scheduler.run(self.directory, now=now)
        self.assertEqual(len(self.catalog.catalog()), 1)
