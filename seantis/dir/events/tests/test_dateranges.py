from datetime import datetime, timedelta

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import utils

class TestDateRanges(IntegrationTestCase):

    def test_next_weekday(self):
        date = datetime(2012, 9, 18, 0, 0) # tuesday

        self.assertEqual(date.weekday(), utils.weekdays['TU'])
        self.assertEqual(utils.next_weekday(date, "TU"), date)
        self.assertEqual(utils.next_weekday(date, "WE"), date + timedelta(days=1))
        self.assertEqual(utils.next_weekday(date, "TH"), date + timedelta(days=2))
        self.assertEqual(utils.next_weekday(date, "MO"), date + timedelta(days=6))

    def test_this_weekend(self):
        date = datetime(2012, 9, 18, 0, 0) # tuesday
        start, end = utils.this_weekend(date)

        self.assertEqual((start.year, start.month, start.day), (2012, 9, 21))
        self.assertEqual(start.weekday(), utils.weekdays["FR"])
        self.assertEqual(start.hour, 16)

        self.assertEqual((end.year, end.month, end.day), (2012, 9, 23))
        self.assertEqual(end.weekday(), utils.weekdays["SU"])
        self.assertEqual(end.hour, 23)
        self.assertEqual(end.minute, 59)
        self.assertEqual(end.second, 59)

        date = datetime(2012, 9, 23, 0, 0) # sunday
        start, end = utils.this_weekend(date)

        self.assertEqual((start.year, start.month, start.day), (2012, 9, 21))
        self.assertEqual((end.year, end.month, end.day), (2012, 9, 23))

        old_start, old_end = start, end

        start, end = utils.this_weekend(start)
        self.assertEqual(start, old_start)
        self.assertEqual(end, old_end)

        start, end = utils.this_weekend(end)
        self.assertEqual(start, old_start)
        self.assertEqual(end, old_end)

    def test_ranges(self):

        start = datetime(2012, 1, 1, 22, 0) # sunday
        end = datetime(2012, 1, 2, 02, 0)
        daterange = utils.DateRangeInfo(start, end)

        daterange.now = datetime(2011, 1, 1, 0, 0)
        self.assertFalse(daterange.is_today)
        self.assertFalse(daterange.is_today)
        self.assertFalse(daterange.is_this_year)
        self.assertTrue(daterange.is_next_year)

        daterange.now = datetime(2012, 1, 1, 12, 0)
        self.assertFalse(daterange.is_over)
        self.assertTrue(daterange.is_today)
        self.assertTrue(daterange.is_this_year)

        daterange.now = datetime(2012, 1, 2, 02, 0)
        self.assertFalse(daterange.is_over)

        daterange.now = datetime(2012, 1, 2, 02, 1)
        self.assertTrue(daterange.is_over)

        daterange.now = datetime(2011, 12, 31, 12, 0) # saturday
        self.assertFalse(daterange.is_today)
        self.assertTrue(daterange.is_tomorrow)
        self.assertTrue(daterange.is_this_week)

        daterange.now = datetime(2011, 12, 24, 12, 0) # saturday one week before
        self.assertTrue(daterange.is_this_week)
        self.assertTrue(daterange.is_next_week) # because end spills over

        daterange.now = datetime(2011, 12, 23, 12, 0) # friday one week before
        self.assertFalse(daterange.is_this_week)
        self.assertTrue(daterange.is_next_week)

        daterange.now = datetime(2012, 1, 2, 12, 0)
        self.assertTrue(daterange.is_over)
        self.assertTrue(daterange.is_this_week)

        daterange.now = datetime(2011, 12, 29, 0, 0) # thursday
        self.assertTrue(daterange.is_this_week)
        self.assertTrue(daterange.is_this_weekend)
        self.assertTrue(daterange.is_next_week) #spillover
        self.assertFalse(daterange.is_next_weekend)

        daterange.now = datetime(2011, 12, 22, 0, 0) # one week earlier
        self.assertFalse(daterange.is_this_week)
        self.assertFalse(daterange.is_this_weekend)
        self.assertTrue(daterange.is_next_week)
        self.assertTrue(daterange.is_next_weekend)

        daterange.now = datetime(2011, 12, 12, 0, 0)
        self.assertFalse(daterange.is_this_month)
        self.assertTrue(daterange.is_next_month)

        daterange.now = datetime(2012, 1, 1, 0, 0)
        self.assertTrue(daterange.is_this_month)
        self.assertFalse(daterange.is_next_month)