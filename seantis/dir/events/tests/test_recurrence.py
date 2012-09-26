from collections import namedtuple
from datetime import datetime, timedelta
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

        item = Item("RRULE:FREQ=DAILY;COUNT=4",
            start=datetime(2012, 1, 1, 10, 0),
            end=datetime(2012, 1, 1, 12, 0)
        )

        occurrences = recurrence.occurrences(item,
            min_date=item.start,
            max_date=item.end
        )

        self.assertEqual(len(occurrences), 1)