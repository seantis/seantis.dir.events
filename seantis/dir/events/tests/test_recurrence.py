# -*- coding: utf-8 -*-

import pytz
import mock

from datetime import datetime, timedelta, date

from zope.publisher.browser import TestRequest

from seantis.dir.events.item import EventsDirectoryItem
from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import recurrence
from seantis.dir.events import dates


class Item(object, EventsDirectoryItem):

    def __init__(self, start, end, recurrence="", timezone='Europe/Zurich',
                 whole_day=False):

        # if this is a whole day, the times are adjusted (this is what
        # plone.app.event would do on the dexterity type)
        if whole_day:
            start = datetime(start.year, start.month, start.day)
            end = datetime(end.year, end.month, end.day, 23, 59, 59)

        # the given date is implicitly of the given timezone, so enforce
        # that and then convert to utc as this is what an EventItem actually
        # stores.
        self.start = dates.to_utc(dates.as_timezone(start, timezone))
        self.end = dates.to_utc(dates.as_timezone(end, timezone))

        self.recurrence = recurrence
        self.timezone = timezone
        self.whole_day = whole_day


class TestRecurrence(IntegrationTestCase):

    def test_occurrences(self):

        item = Item(
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0),
            "RRULE:FREQ=DAILY;COUNT=4"
        )

        occurrences = recurrence.occurrences(
            item,
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

        occurrences = recurrence.occurrences(
            item, min_date=item.start, max_date=item.end
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
        occurrences = recurrence.occurrences(
            item,
            min_date=datetime(2011, 1, 1, tzinfo=item.tz),
            max_date=datetime(2011, 1, 1, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [])

        non_recurrant = Item(
            datetime(2012, 1, 1, 10, 0),
            datetime(2012, 1, 1, 12, 0)
        )

        occurrences = recurrence.occurrences(
            non_recurrant,
            min_date=datetime(2011, 1, 1, tzinfo=item.tz),
            max_date=datetime(2011, 1, 1, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [])

        # non-recurring items are packed into a list
        occurrences = recurrence.occurrences(
            non_recurrant,
            datetime(2012, 1, 1, 10, 0, tzinfo=item.tz),
            datetime(2012, 1, 1, 12, 0, tzinfo=item.tz)
        )

        self.assertEqual(occurrences, [non_recurrant])

    def test_split_days(self):
        # split needed?

        def assert_split(num, daterange):
            start, end = daterange.split(' - ')
            start = datetime.strptime('2012.' + start, '%Y.%d.%m %H:%M')
            end = datetime.strptime('2012.' + end, '%Y.%d.%m %H:%M')
            self.assertEqual(dates.split_days_count(start, end), num)

        assert_split(0, "01.01 08:00 - 01.01 17:00")

        assert_split(0, "01.01 16:00 - 02.01 02:00")
        assert_split(0, "01.01 00:00 - 02.01 08:59")

        assert_split(1, "01.01 16:00 - 02.01 09:00")
        assert_split(1, "01.01 16:00 - 02.01 23:00")
        assert_split(1, "01.01 00:00 - 02.01 23:00")

        assert_split(2, "01.01 00:00 - 03.01 09:00")

        two_days = Item(
            datetime(2012, 1, 1, 10),
            datetime(2012, 1, 2, 20),
            timezone='utc'
        )

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

        # one split
        two_days = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 2, 10))
        splits = list(recurrence.split_days(two_days))

        self.assertEqual(len(splits), 2)

        two_days = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 2, 9))
        splits = list(recurrence.split_days(two_days))

        self.assertEqual(len(splits), 2)

        # no split
        one_day = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 2, 8))
        splits = list(recurrence.split_days(one_day))

        self.assertEqual(len(splits), 1)

        # more days
        three_days = Item(datetime(2012, 1, 1, 10), datetime(2012, 1, 3, 20))
        splits = list(recurrence.split_days(three_days))

        self.assertEqual(len(splits), 3)

        self.assertEqual(splits[0].local_start.hour, 10)
        self.assertEqual(splits[0].local_end.hour, 23)
        self.assertEqual(splits[0].local_end.minute, 59)
        self.assertEqual(splits[0].local_end.second, 59)

        self.assertEqual(splits[1].local_start.hour, 0)
        self.assertEqual(splits[1].local_end.hour, 23)
        self.assertEqual(splits[1].local_end.minute, 59)
        self.assertEqual(splits[1].local_end.second, 59)

        self.assertEqual(splits[2].local_start.hour, 0)
        self.assertEqual(splits[2].local_start.minute, 0)
        self.assertEqual(splits[2].local_start.second, 0)
        self.assertEqual(splits[2].local_end.hour, 20)

        # whole_day events
        three_whole_days = Item(
            datetime(2012, 1, 1),
            datetime(2012, 1, 3),
            timezone='utc',
            whole_day=True
        )

        self.assertTrue(
            dates.is_whole_day(three_whole_days.start, three_whole_days.end)
        )

        splits = list(recurrence.split_days(three_whole_days))
        self.assertEqual(len(splits), 3)
        self.assertEqual([1, 2, 3], [s.start.day for s in splits])
        self.assertEqual([1, 2, 3], [s.end.day for s in splits])

    @mock.patch('seantis.dir.events.dates.default_timezone')
    @mock.patch('seantis.dir.events.dates.default_now')
    def test_cornercases(self, default_now, default_timezone):

        default_timezone.return_value = 'Europe/Zurich'

        # create an event that repeats every sunday at 7 in the morning
        # over a period within which daylight savings time changes
        item = Item(
            datetime(2012, 10, 21, 7),
            datetime(2012, 11, 4, 7),
            "RRULE:FREQ=WEEKLY",
            timezone='Europe/Zurich'
        )

        occurrences = recurrence.occurrences(
            item, min_date=item.local_start, max_date=item.local_end
        )

        self.assertEqual(len(occurrences), 3)
        self.assertEqual([o.local_start.hour for o in occurrences], [7] * 3)
        self.assertEqual(
            [o.local_start.weekday() for o in occurrences], [6] * 3
        )

        # create an event that starts at 0:00 in a timezone other than
        # utc and ensure that the resulting human date shows the
        # correct weekday in the given timezone
        # to make it tricky, cross over daylight savings time

        default_now.return_value = datetime(
            2012, 10, 17, tzinfo=pytz.timezone('Europe/Zurich')
        )

        start = datetime(2012, 10, 30)
        item = Item(
            start, start + timedelta(seconds=60 * 60 * 2),
            timezone='Europe/Zurich'
        )

        # behold, the Swiss German language
        request = TestRequest()
        request.locale.dates.calendars['gregorian'].getDayNames = mock.Mock(
            return_value=[
                u'Mäntig', u'Zischtig', u'Mittwuch', u'Dunschtig', u'Fritig',
                u'Samschtig', u'Sunntig'
            ]
        )
        human = item.as_occurrence().human_date(request)

        self.assertTrue(u'Zischtig' in human)

        # while we're at it
        human = item.as_occurrence().human_daterange(request)
        self.assertEqual(human, '00:00 - 02:00')

    def test_has_future_occurrences(self):
        item = Item(
            datetime(2013, 1, 1), datetime(2013, 1, 2), timezone='utc'
        )

        reference = dates.to_utc(datetime(2013, 1, 3))
        self.assertFalse(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 2))
        self.assertFalse(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 1))
        self.assertTrue(recurrence.has_future_occurrences(item, reference))

        item = Item(
            datetime(2013, 1, 1), datetime(2013, 1, 2), timezone='utc',
                recurrence='RRULE:FREQ=DAILY;UNTIL=20130105T000000Z'
        )

        reference = dates.to_utc(datetime(2013, 1, 4))
        self.assertTrue(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 5))
        self.assertTrue(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 6))
        self.assertFalse(recurrence.has_future_occurrences(item, reference))

        # the recurrence rule may come without a timezone (missing Z)

        item = Item(
            datetime(2013, 1, 1), datetime(2013, 1, 2), timezone='utc',
                recurrence='RRULE:FREQ=DAILY;UNTIL=20130105T000000'
        )

        reference = dates.to_utc(datetime(2013, 1, 4))
        self.assertTrue(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 5))
        self.assertTrue(recurrence.has_future_occurrences(item, reference))

        reference = dates.to_utc(datetime(2013, 1, 6))
        self.assertFalse(recurrence.has_future_occurrences(item, reference))
