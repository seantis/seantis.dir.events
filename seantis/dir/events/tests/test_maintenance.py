from datetime import datetime, timedelta
from DateTime.DateTime import DateTime

from seantis.dir.events.dates import to_utc
from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import maintenance


class TestMaintenance(IntegrationTestCase):

    def setUp(self):
        super(TestMaintenance, self).setUp()
        # login to gain the right to create events
        self.login_admin()

    def tearDown(self):
        super(TestMaintenance, self).tearDown()
        self.logout()

    def test_remove_stale_previews(self):
        preview = self.create_event()
        self.assertEqual(preview.state, 'preview')

        run = lambda: maintenance.remove_stale_previews(
            self.directory, dryrun=True
        )

        self.assertEqual(run(), [])

        preview.modification_date = DateTime(
            datetime.utcnow() - timedelta(days=2, microseconds=1)
        )
        preview.reindexObject(idxs=['modified'])

        self.assertEqual(run(), [preview.id])

        preview.submit()

        self.assertEqual(run(), [])

    def test_archive_past_events(self):

        run = lambda: maintenance.archive_past_events(
            self.directory, dryrun=True
        )

        published = self.create_event()
        self.assertEqual(run(), [])

        published.submit()
        self.assertEqual(run(), [])

        published.publish()
        self.assertEqual(run(), [])

        published.start = to_utc(datetime.utcnow() - timedelta(days=3))
        published.end = to_utc(datetime.utcnow() - timedelta(days=3))
        published.reindexObject(idxs=['start', 'end'])

        self.assertEqual(run(), [published.id])

        published.start += timedelta(days=2)
        published.end += timedelta(days=2)
        published.reindexObject(idxs=['start', 'end'])
        self.assertEqual(run(), [])

        published.start = to_utc(datetime.utcnow() - timedelta(days=3))
        published.end = to_utc(datetime.utcnow() - timedelta(days=3))
        published.reindexObject(idxs=['start', 'end'])
        self.assertEqual(run(), [published.id])

        published.recurrence = 'RRULE:FREQ=WEEKLY;COUNT=10'
        self.assertEqual(run(), [])

        published.start = to_utc(datetime.utcnow() - timedelta(days=100))
        published.end = to_utc(datetime.utcnow() - timedelta(days=100))
        published.recurrence = 'RRULE:FREQ=WEEKLY;COUNT=3'
        published.reindexObject(idxs=['start', 'end'])

        self.assertEqual(run(), [published.id])

    def test_remove_archived_events(self):

        run = lambda: maintenance.remove_archived_events(
            self.directory, dryrun=True
        )

        archived = self.create_event()
        self.assertEqual(run(), [])

        archived.submit()
        self.assertEqual(run(), [])

        archived.publish()
        self.assertEqual(run(), [])

        archived.start = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=31))
        archived.reindexObject(idxs=['start', 'end'])
        self.assertEqual(run(), [])

        archived.archive()
        self.assertEqual(run(), [archived.id])

        archived.start = to_utc(datetime.utcnow() - timedelta(days=10))
        archived.end = to_utc(datetime.utcnow() - timedelta(days=10))
        archived.reindexObject(idxs=['start', 'end'])

        self.assertEqual(run(), [])
