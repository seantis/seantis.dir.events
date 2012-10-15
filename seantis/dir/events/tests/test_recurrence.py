import pytz

from collections import namedtuple
from datetime import datetime, timedelta, date
from dateutil.tz import tzutc

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import recurrence

class Item(object):
    
    def __init__(self, start, end, recurrence="", timezone=None):
        self.timezone = timezone or 'Europe/Zurich'
        self.start = start.replace(tzinfo=self.tz)
        self.end = end.replace(tzinfo=self.tz)
        
        self.recurrence = recurrence

    @property
    def tz(self):
        return pytz.timezone(self.timezone)

    @property
    def local_start(self):
        return self.start.astimezone(self.tz)

    @property
    def local_end(self):
        return self.end.astimezone(self.tz)

    def as_occurrence(self):
        return recurrence.Occurrence(self, self.start, self.end)

class TestRecurrence(IntegrationTestCase):

    def test_occurrences(self):

        item = Item(
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0),
            "RRULE:FREQ=DAILY;COUNT=4"
        )

        occurrences = recurrence.occurrences(item, 
            min_date=datetime(2012, 1, 1, 0, 0, tzinfo=item.tz),
            max_date=datetime(2012, 12, 31, 0, 0, tzinfo=item.tz)
        )

        self.assertEqual(len(occurrences), 4)
        
        for occurrence in occurrences:
            self.assertEqual(occurrence.recurrence, item.recurrence)

        days = [o.start.day for o in occurrences]
        self.assertEqual([1, 2, 3, 4], days)

        # test occurrences
        item = Item(
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0),
            "RRULE:FREQ=DAILY;COUNT=4"
        )

        occurrences = recurrence.occurrences(item,
            min_date=item.start,
            max_date=item.end
        )

        self.assertEqual(len(occurrences), 1)

        # see if the picking works correctly
        for i in range(1, 5):
            picked = recurrence.pick_occurrence(item, start=date(2012, 1, i))
            self.assertEqual(picked.start.day, i)
            self.assertEqual(picked.start.month, 1)
            self.assertEqual(picked.start.year, 2012)

        picked = recurrence.pick_occurrence(item, start=date(2011, 12, 31))
        self.assertEqual(picked, None)

        picked = recurrence.pick_occurrence(item, start=date(2012, 1, 5))
        self.assertEqual(picked, None)

        # occurrences should return an empty list in these cases
        occurrences = recurrence.occurrences(item,
            min_date=datetime(2011, 1, 1, tzinfo=item.tz),
            max_date=datetime(2011, 1, 1, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [])

        non_recurrant = Item( 
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0)
        )

        occurrences = recurrence.occurrences(non_recurrant,
            min_date=datetime(2011, 1, 1, tzinfo=item.tz),
            max_date=datetime(2011, 1, 1, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [])

        # non-recurring items are packed into a list
        occurrences = recurrence.occurrences(non_recurrant,
            datetime(2012, 1, 1, 10, 0, tzinfo=item.tz),
            datetime(2012, 1, 1, 12, 0, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [non_recurrant])

    def test_split_days(self):
        Item = namedtuple("Item", ["start", "end"])

        two_days = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 2, 20))

        splits = list(recurrence.split_days(two_days))
        self.assertEqual(len(splits), 2)

        self.assertEqual(splits[0].start.hour, 10)
        self.assertEqual(splits[0].end.hour, 23)
        self.assertEqual(splits[0].end.minute, 59)
        self.assertEqual(splits[0].end.second, 59)

        self.assertEqual(splits[1].start.hour, 0)
        self.assertEqual(splits[1].start.minute, 0)
        self.assertEqual(splits[1].start.second, 0)
        self.assertEqual(splits[1].end.hour, 20)

        # >= 24hours
        one_day = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 2, 10))
        splits = list(recurrence.split_days(one_day))
        
        self.assertEqual(len(splits), 2)

        # < 24 hours
        one_day = Item(
            datetime(2012, 1, 1, 10), 
            datetime(2012, 1, 2, 10) - timedelta(microseconds=1)
        )
        splits = list(recurrence.split_days(one_day))

        self.assertEqual(len(splits), 1)

        # more days
        three_days = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 3, 20))
        splits = list(recurrence.split_days(three_days))

        self.assertEqual(len(splits), 3)

        self.assertEqual(splits[0].start.hour, 10)
        self.assertEqual(splits[0].end.hour, 23)
        self.assertEqual(splits[0].end.minute, 59)
        self.assertEqual(splits[0].end.second, 59)

        self.assertEqual(splits[1].start.hour, 0)
        self.assertEqual(splits[1].end.hour, 23)
        self.assertEqual(splits[1].end.minute, 59)
        self.assertEqual(splits[1].end.second, 59)

        self.assertEqual(splits[2].start.hour, 0)
        self.assertEqual(splits[2].start.minute, 0)
        self.assertEqual(splits[2].start.second, 0)
        self.assertEqual(splits[2].end.hour, 20)