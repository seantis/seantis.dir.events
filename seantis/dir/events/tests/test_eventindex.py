import transaction

from datetime import date
from seantis.dir.events.tests import IntegrationTestCase

from seantis.dir.events.catalog import LazyList, EventOrderIndex

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

        submitted = self.catalog.indices['submitted']
        published = self.catalog.indices['published']

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        event = self.create_event()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        event.submit()
        transaction.commit()

        self.assertEqual(len(submitted.index), 1)
        self.assertEqual(len(published.index), 0)

        event.publish()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 1)

        event.archive()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

    def test_event_order_index_recurrence(self):
        self.login_testuser()

        submitted = self.catalog.indices['submitted']
        published = self.catalog.indices['published']

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        event = self.create_event(recurrence='RRULE:FREQ=DAILY;COUNT=10')
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        event.submit()
        transaction.commit()

        self.assertEqual(len(submitted.index), 10)
        self.assertEqual(len(published.index), 0)

        event.publish()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 10)

        event.recurrence = ''
        transaction.commit()

        event.reindexObject()
        event.reindex()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 1)

        event.archive()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

    def test_eventorder_metadata(self):

        class MockCatalog(object):

            def __init__(self, directory):
                self.directory = directory

        def generate_metadata(testindex):

            orderindex = EventOrderIndex(
                catalog=MockCatalog(self.directory), state='published',
                initial_index=testindex
            )

            orderindex.generate_metadata()
            return orderindex.get_metadata('dateindex')

        dateindex = generate_metadata([
            '12.01.01-12:00;'
        ])

        self.assertTrue(date(2012, 1, 1) in dateindex)
        self.assertEqual(dateindex[date(2012, 1, 1)], 0)
        self.assertEqual(len(dateindex), 1)

        dateindex = generate_metadata([
            '12.01.01-00:00;',
            '12.01.01-23:59;'
        ])

        self.assertTrue(date(2012, 1, 1) in dateindex)
        self.assertEqual(dateindex[date(2012, 1, 1)], 0)
        self.assertEqual(len(dateindex), 1)

        dateindex = generate_metadata([
            '12.01.01-00:00;',
            '12.01.01-00:00;',
            '12.01.02-00:00;'
        ])

        self.assertTrue(date(2012, 1, 1) in dateindex)
        self.assertTrue(date(2012, 1, 2) in dateindex)
        self.assertEqual(dateindex[date(2012, 1, 1)], 0)
        self.assertEqual(dateindex[date(2012, 1, 2)], 2)
        self.assertEqual(len(dateindex), 2)

        dateindex = generate_metadata([
            '12.01.01-00:00',
            '12.09.07-00:00',
            '12.12.31-00:00'
        ])

        self.assertEqual(dateindex[date(2012, 1, 1)], 0)
        self.assertEqual(dateindex[date(2012, 1, 2)], 1)
        self.assertEqual(dateindex[date(2012, 9, 6)], 1)
        self.assertEqual(dateindex[date(2012, 9, 7)], 1)
        self.assertEqual(dateindex[date(2012, 9, 8)], 2)
        self.assertEqual(dateindex[date(2012, 12, 30)], 2)
        self.assertEqual(dateindex[date(2012, 12, 31)], 2)
        self.assertEqual(len(dateindex), 366)

        dateindex = generate_metadata([
            '13.07.04-14:00;',
            '13.07.05-18:45;',
            '13.07.05-19:00;',
            '13.07.05-19:00;',
            '13.07.05-19:00;',
            '13.07.06-19:00;',
        ])

        self.assertTrue(date(2013, 07, 04) in dateindex)
        self.assertTrue(date(2013, 07, 05) in dateindex)
        self.assertTrue(date(2013, 07, 06) in dateindex)

        self.assertEqual(dateindex[date(2013, 07, 04)], 0)
        self.assertEqual(dateindex[date(2013, 07, 05)], 1)
        self.assertEqual(dateindex[date(2013, 07, 06)], 5)
