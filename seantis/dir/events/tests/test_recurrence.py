from collections import namedtuple
from datetime import datetime, timedelta, date
from dateutil.tz import tzutc

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import recurrence



class TestRecurrence(IntegrationTestCase):

    def test_occurrences(self):
        Item = namedtuple('Item', ['recurrence', 'start', 'end'])

        # timezones may be used. if they are, all dates are either timezone
        # aware or timezone naive. No mixing
        def timezone_occurrences(timezone):
            item = Item("RRULE:FREQ=DAILY;COUNT=4", 
                start=datetime(2012, 1, 1, 10, 0, tzinfo=timezone),
                end=datetime(2012, 1, 1, 12, 0, tzinfo=timezone)
            )

            occurrences = recurrence.occurrences(item, 
                min_date=datetime(2012, 1, 1, 0, 0, tzinfo=timezone),
                max_date=datetime(2012, 12, 31, 0, 0, tzinfo=timezone)
            )

            self.assertEqual(len(occurrences), 4)
            
            for occurrence in occurrences:
                self.assertEqual(occurrence.recurrence, item.recurrence)

            days = [o.start.day for o in occurrences]
            self.assertEqual([1, 2, 3, 4], days)

            return occurrences

        for occurrence in timezone_occurrences(timezone=None):
            self.assertEqual(occurrence.start.tzinfo, None)

        for occurrence in timezone_occurrences(timezone=tzutc()):
            self.assertEqual(occurrence.start.tzinfo, tzutc())

        # test occurrences
        item = Item("RRULE:FREQ=DAILY;COUNT=4",
            start=datetime(2012, 1, 1, 10, 0),
            end=datetime(2012, 1, 1, 12, 0)
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
            min_date=datetime(2011, 1, 1),
            max_date=datetime(2011, 1, 1)
        )

        self.assertEqual(occurrences, [])

        non_recurrant = Item("", 
            start=datetime(2012, 1, 1, 10, 0),
            end=datetime(2012, 1, 1, 12, 0)
        )

        occurrences = recurrence.occurrences(non_recurrant,
            min_date=datetime(2011, 1, 1),
            max_date=datetime(2011, 1, 1)
        )

        self.assertEqual(occurrences, [])

        # non-recurring items are packed into a list
        occurrences = recurrence.occurrences(non_recurrant,
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0)
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