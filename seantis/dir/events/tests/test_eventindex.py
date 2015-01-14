import transaction

from datetime import date, datetime
from seantis.dir.events import dates
from seantis.dir.events.tests import IntegrationTestCase

from seantis.dir.events.catalog import (
    LazyList,
    EventOrderIndex,
    attach_reindex_to_transaction,
    ReindexDataManager,
)

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

        event.publish()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 1)

        denied = self.create_event()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 1)

        denied.submit()
        transaction.commit()

        self.assertEqual(len(submitted.index), 1)
        self.assertEqual(len(published.index), 1)

        denied.do_action("deny")
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 1)

    def test_event_order_index_more(self):

        self.login_testuser()

        submitted = self.catalog.indices['submitted']
        published = self.catalog.indices['published']

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        # Lazy-create events on access
        events = LazyList(lambda i: self.create_event(), 50)

        num_submitted = 0
        num_published = 0

        for new_idx, new_event in enumerate(events):

            if new_idx > 0:

                for old_idx, old_event in enumerate(events[:new_idx - 1]):

                    if old_event.state == 'preview':

                        if (old_idx % 13 != 0):
                            old_event.submit()
                            transaction.commit()
                            num_submitted += 1

                    elif old_event.state == 'submitted':

                        if (old_idx % 7 != 0):
                            old_event.publish()
                            transaction.commit()
                            num_submitted -= 1
                            num_published += 1
                        else:
                            old_event.do_action("deny")
                            transaction.commit()
                            num_submitted -= 1

                    elif old_event.state == 'published':

                        if (old_idx % 5 != 0):
                            old_event.archive()
                            transaction.commit()
                            num_published -= 1

                    elif old_event.state == 'archived':

                        if (old_idx % 11 == 0):
                            old_event.publish()
                            transaction.commit()
                            num_published += 1

                    self.assertEqual(len(submitted.index), num_submitted)
                    self.assertEqual(len(published.index), num_published)

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

        event.archive()
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
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

        denied = self.create_event(recurrence='RRULE:FREQ=DAILY;COUNT=10')
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        denied.submit()
        transaction.commit()

        self.assertEqual(len(submitted.index), 10)
        self.assertEqual(len(published.index), 0)

        denied.do_action("deny")
        transaction.commit()

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

    def test_event_order_index_recurrence_more(self):

        self.login_testuser()

        submitted = self.catalog.indices['submitted']
        published = self.catalog.indices['published']

        self.assertEqual(len(submitted.index), 0)
        self.assertEqual(len(published.index), 0)

        events = LazyList(lambda i: self.create_event(
            recurrence='RRULE:FREQ=DAILY;COUNT=' + str(i)), 50)

        num_submitted = 0
        num_published = 0

        for new_idx, new_event in enumerate(events):

            if new_idx > 0:

                for old_idx, old_event in enumerate(events[:new_idx - 1]):

                    if old_event.state == 'preview':

                        if (old_idx % 13 != 0):
                            old_event.submit()
                            transaction.commit()
                            num_submitted += old_idx

                    elif old_event.state == 'submitted':

                        if (old_idx % 7 != 0):
                            old_event.publish()
                            transaction.commit()
                            num_submitted -= old_idx
                            num_published += old_idx
                        else:
                            old_event.do_action("deny")
                            transaction.commit()
                            num_submitted -= old_idx

                    elif old_event.state == 'published':

                        if (old_idx % 5 != 0):
                            old_event.archive()
                            transaction.commit()
                            num_published -= old_idx

                    elif old_event.state == 'archived':

                        if (old_idx % 11 == 0):
                            old_event.publish()
                            transaction.commit()
                            num_published += old_idx

                    self.assertEqual(len(submitted.index), num_submitted)
                    self.assertEqual(len(published.index), num_published)

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

    def test_attach_reindex_idempotence(self):

        # attaching the reindex to the request multiple times should
        # result in only one call to the reindex function on the catalog

        # because we cannot let the transaction go through in the test
        # we need to inspect the content of the transaction
        def number_of_data_managers():
            resources = transaction.get()._resources
            return len(
                [m for m in resources if isinstance(m, ReindexDataManager)]
            )

        attach_reindex_to_transaction(self.directory)
        self.assertEqual(1, number_of_data_managers())
        attach_reindex_to_transaction(self.directory)
        self.assertEqual(1, number_of_data_managers())
        attach_reindex_to_transaction(self.directory)
        self.assertEqual(1, number_of_data_managers())

    def test_by_range_timezone_regression(self):
        year = date.today().year

        self.login_testuser()

        published = self.catalog.indices['published']

        self.assertEqual(len(published.index), 0)

        event = self.create_event(
            start=datetime(year, 12, 31, 22),
            end=datetime(year, 12, 31, 23),
            timezone='Europe/Vienna'
        )
        event.submit()
        event.publish()
        transaction.commit()

        self.assertEqual(len(published.index), 1)

        dtrange = (datetime(year+1, 1, 1), datetime(year+1, 12, 31))
        dtrange = [dates.as_timezone(dt, 'Europe/Vienna') for dt in dtrange]
        self.assertEqual(len(published.by_range(*dtrange)), 0)

        dtrange = (datetime(year, 1, 1), datetime(year, 12, 31, 23, 59))
        dtrange = [dates.as_timezone(dt, 'Europe/Vienna') for dt in dtrange]
        self.assertEqual(len(published.by_range(*dtrange)), 1)
