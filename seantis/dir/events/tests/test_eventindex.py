from seantis.dir.events.tests import IntegrationTestCase

from seantis.dir.events.catalog import LazyList

from mock import Mock


class TestEventIndex(IntegrationTestCase):

    def test_lazy_list(self):

        # test indexing
        lazy = LazyList(Mock(), 10)
        self.assertEqual(len(lazy), 10)
        self.assertEqual(lazy._get_item.call_count, 0)

        lazy[0]
        self.assertEqual(lazy._get_item.call_count, 1)

        lazy[1]
        self.assertEqual(lazy._get_item.call_count, 2)

        self.assertRaises(IndexError, lambda: lazy[10])

        # test iterating
        lazy = LazyList(Mock(), 10)
        [i for i in lazy]
        self.assertEqual(lazy._get_item.call_count, 10)

        # test_slicing
        lazy = LazyList(Mock(), 10)
        lazy[:2]
        self.assertEqual(lazy._get_item.call_count, 2)

        lazy = LazyList(Mock(), 10)
        lazy[5:100]
        self.assertEqual(lazy._get_item.call_count, 5)

    def test_event_order_index(self):

        self.login_testuser()

        index = self.catalog.orderindex

        self.assertEqual(len(index.index), 0)

        event = self.create_event()

        self.assertEqual(len(index.index), 0)

        event.submit()

        self.assertEqual(len(index.index), 0)

        event.publish()

        self.assertEqual(len(index.index), 1)

        event.archive()

        self.assertEqual(len(index.index), 0)

        event = self.create_event(recurrence='RRULE:FREQ=DAILY;COUNT=10')
        event.submit()
        event.publish()

        self.assertEqual(len(index.index), 10)

        event.recurrence = ''
        event.reindex()

        self.assertEqual(len(index.index), 1)

        event.archive()

        self.assertEqual(len(index.index), 0)
