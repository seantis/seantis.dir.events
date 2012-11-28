from datetime import datetime, timedelta

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import dates


class TestDateRanges(IntegrationTestCase):

    def test_next_weekday(self):
        date = datetime(2012, 9, 18, 0, 0)  # tuesday

        self.assertEqual(date.weekday(), dates.weekdays['TU'])
        self.assertEqual(dates.next_weekday(date, "TU"), date)
        self.assertEqual(
            dates.next_weekday(date, "WE"), date + timedelta(days=1)
        )
        self.assertEqual(
            dates.next_weekday(date, "TH"), date + timedelta(days=2)
        )
        self.assertEqual(
            dates.next_weekday(date, "MO"), date + timedelta(days=6)
        )

    def test_this_weekend(self):
        date = datetime(2012, 9, 18, 0, 0)  # tuesday
        start, end = dates.this_weekend(date)

        self.assertEqual((start.year, start.month, start.day), (2012, 9, 21))
        self.assertEqual(start.weekday(), dates.weekdays["FR"])
        self.assertEqual(start.hour, 16)

        self.assertEqual((end.year, end.month, end.day), (2012, 9, 23))
        self.assertEqual(end.weekday(), dates.weekdays["SU"])
        self.assertEqual(end.hour, 23)
        self.assertEqual(end.minute, 59)
        self.assertEqual(end.second, 59)

        date = datetime(2012, 9, 23, 0, 0)  # sunday
        start, end = dates.this_weekend(date)

        self.assertEqual((start.year, start.month, start.day), (2012, 9, 21))
        self.assertEqual((end.year, end.month, end.day), (2012, 9, 23))

        old_start, old_end = start, end

        start, end = dates.this_weekend(start)
        self.assertEqual(start, old_start)
        self.assertEqual(end, old_end)

        start, end = dates.this_weekend(end)
        self.assertEqual(start, old_start)
        self.assertEqual(end, old_end)

    def test_morning(self):

        dateranges = dates.DateRanges()
        dateranges.now = datetime.today()
        overlaps = lambda: dateranges.overlaps('today', start, end)

        start = datetime.today().replace(hour=1, minute=0)
        end = datetime.today().replace(hour=4, minute=0)
        self.assertTrue(overlaps())

        start = datetime.today().replace(hour=1, minute=0)
        end = datetime.today().replace(hour=3, minute=0)
        self.assertTrue(overlaps())

        start = datetime.today().replace(hour=1, minute=0)
        end = datetime.today().replace(hour=2, minute=59)
        self.assertFalse(overlaps())

    def test_ranges(self):

        start = datetime(2012, 1, 1, 22, 0)  # sunday
        end = datetime(2012, 1, 2, 03, 0)
        dateranges = dates.DateRanges()
        overlaps = lambda method: dateranges.overlaps(method, start, end)

        dateranges.now = datetime(2011, 1, 1, 0, 0)
        self.assertFalse(overlaps('today'))
        self.assertFalse(overlaps('this_year'))
        self.assertTrue(overlaps('next_year'))
        self.assertTrue(overlaps('this_and_next_year'))

        dateranges.now = datetime(2012, 1, 1, 12, 0)
        self.assertTrue(overlaps('today'))
        self.assertTrue(overlaps('this_year'))
        self.assertTrue(overlaps('this_and_next_year'))

        dateranges.now = datetime(2011, 12, 31, 12, 0)  # saturday
        self.assertFalse(overlaps('today'))
        self.assertTrue(overlaps('tomorrow'))
        self.assertTrue(overlaps('this_week'))

        dateranges.now = datetime(2011, 12, 24, 12, 0)  # sat. one week before
        self.assertTrue(overlaps('this_week'))
        self.assertTrue(overlaps('next_week'))  # spillover

        dateranges.now = datetime(2011, 12, 23, 12, 0)  # fri. one week before
        self.assertFalse(overlaps('this_week'))
        self.assertTrue(overlaps('next_week'))

        dateranges.now = datetime(2012, 1, 2, 12, 0)
        self.assertTrue(overlaps('this_week'))

        dateranges.now = datetime(2011, 12, 29, 0, 0)  # thursday
        self.assertTrue(overlaps('this_week'))
        self.assertTrue(overlaps('this_weekend'))
        self.assertTrue(overlaps('next_week'))  # spillover
        self.assertFalse(overlaps('next_weekend'))

        dateranges.now = datetime(2011, 12, 22, 0, 0)  # one week earlier
        self.assertFalse(overlaps('this_week'))
        self.assertFalse(overlaps('this_weekend'))
        self.assertTrue(overlaps('next_week'))
        self.assertTrue(overlaps('next_weekend'))

        dateranges.now = datetime(2011, 12, 12, 0, 0)
        self.assertFalse(overlaps('this_month'))
        self.assertTrue(overlaps('next_month'))

        dateranges.now = datetime(2012, 1, 1, 0, 0)
        self.assertTrue(overlaps('this_month'))
        self.assertFalse(overlaps('next_month'))
