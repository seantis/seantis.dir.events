import pytz

from itertools import groupby
from collections import OrderedDict
from datetime import datetime, timedelta

from zope.proxy import ProxyBase
from urllib import urlencode

from plone.event.recurrence import recurrence_sequence_ical
from plone.event.utils import utcoffset_normalize, DSTADJUST

from seantis.dir.events import dates
from seantis.dir.events.dates import overlaps


class Occurrence(ProxyBase):

    """ plone.app.event creates occurrences using adapters, which seems
    a bit wasteful to me. It also doesn't play too well with my interfaces,
    overridding either my title/description attributes ore not
    showing my methods.

    This pure proxy has none of those problems.

    ========================================================================
    THERE IS ONE CAVEAT. In templates "context/start" will yield the wrapped
    item's start. "python: context.start" on the other hand will yield the
    occurence's start. Same with other properties/methods
    ========================================================================
    """

    __slots__ = (
        '_wrapped', '_start', '_end', '_unsplit_start', '_unsplit_end'
    )

    def __init__(self, item, start, end, unsplit_start=None, unsplit_end=None):
        self._wrapped = item
        self._start = start
        self._end = end
        self._unsplit_start = unsplit_start
        self._unsplit_end = unsplit_end

    def __new__(cls, item, *args, **kwargs):
        return ProxyBase.__new__(cls, item)

    def get_object(self):
        """ Wraps the underlying getObject of the brain, ensuring that the
        result is still an occurrence with the same characteristics.

        """
        if hasattr(self._wrapped, 'getObject'):
            return Occurrence(
                self._wrapped.getObject(),
                self._start,
                self._end,
                self._unsplit_start,
                self._unsplit_end
            )
        else:
            return self

    @property
    def tz(self):
        return pytz.timezone(self.timezone)

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def local_start(self):
        return self.tz.normalize(self.start)

    @property
    def local_end(self):
        return self.tz.normalize(self.end)

    @property
    def real_start(self):
        return self._wrapped.start

    @property
    def real_end(self):
        return self._wrapped.end

    @property
    def real_local_start(self):
        return self.tz.normalize(self._wrapped.start)

    @property
    def real_local_end(self):
        return self.tz.normalize(self._wrapped.end)

    @property
    def unsplit_start(self):
        return self._unsplit_start

    @property
    def unsplit_end(self):
        return self._unsplit_end

    def url(self):
        """ Adds the date of the occurrence to the result of absolute_url. This
        allows to distinguish between occurrences.

        There would be two other options, but they are less ideal:

        1. Add the whole date-time string - Results in a less than pretty url.
        2. Add an occurrence count - The underlying item of the url might
        change without any chance to tell the user.

        """
        base = self._wrapped.absolute_url()

        # don't add anything if the wrapped item doesn't have recurrence
        if not self._wrapped.recurrence:
            return base

        base += '?' in base and '&' or '?'
        return base + urlencode({'date': self._start.strftime('%Y-%m-%d')})

    def human_date(self, request):
        return dates.human_date(self.local_start, request)

    def human_date_short(self, request):
        return dates.human_date_short(self.local_start, request)

    def human_daterange(self, request):
        # occurrences split to days all get the same date string
        if all((self.unsplit_start, self.unsplit_end)):
            start = self.unsplit_start
            end = self.unsplit_end
        else:
            start = self.start
            end = self.end

        start = self.tz.normalize(start)
        end = self.tz.normalize(end)

        return dates.human_daterange(start, end, request)


def grouped_occurrences(occurrences, request):
    """ Returns the given occurrences grouped by human_date_short. """

    def groupkey(item):
        date = item.human_date_short(request)
        return date

    groups = groupby(sorted(occurrences, key=lambda o: o.start), groupkey)

    # Zope Page Templates don't know how to handle generators :-|
    result = OrderedDict()

    for group in groups:
        result[group[0]] = [i for i in group[1]]

    return result


def pick_occurrence(item, start):
    """ Returns the occurrence at startdate. This suffices because two
    occurrences of the same item are never on the same day.

    """

    min_date = datetime(
        start.year, start.month, start.day,
        tzinfo=item.local_start.tzinfo
    )
    max_date = min_date + timedelta(days=1, microseconds=-1)

    found = occurrences(item, min_date, max_date)
    assert len(found) in (0, 1), "Multiple occurences on the same day?"

    return found and found[0] or None


def split_days(occurrence):
    """ Iterates through a list of occurrences and splits the occurrences
    which span more than 24 hours into sub-occurrences. The idea is to
    have events that last multiple days display on each day separately.

    """
    original_start = occurrence.local_start
    original_end = occurrence.local_end

    days = dates.split_days_count(original_start, original_end)

    if not days:
        yield occurrence
    else:
        for day in xrange(0, days + 1):
            first_day = day == 0
            last_day = day == days

            if first_day:
                start = original_start
            else:
                start = datetime(
                    original_start.year,
                    original_start.month,
                    original_start.day,
                    tzinfo=original_start.tzinfo
                ) + timedelta(days=day)

            if last_day:
                end = original_end
            else:
                end = datetime(
                    original_start.year,
                    original_start.month,
                    original_start.day,
                    tzinfo=original_start.tzinfo
                ) + timedelta(days=day + 1, microseconds=-1)

            start, end = map(dates.to_utc, (start, end))

            # if the given occurrence is already a proxy, don't double-wrap it
            if isinstance(occurrence, Occurrence):
                yield Occurrence(
                    occurrence._wrapped,
                    start, end, original_start, original_end
                )
            else:
                yield Occurrence(
                    occurrence,
                    start, end, original_start, original_end
                )


def occurrences_over_limit(rule, start, limit):

    assert rule and start and limit

    for i, o in enumerate(recurrence_sequence_ical(start=start, recrule=rule)):
        if i + 1 > limit:
            return True

    return False


def occurrences(item, min_date, max_date):
    """ Returns the occurrences for item between min and max date.
    Will return a list with a single item if the given item has no recurrence.

    """

    if not isinstance(item.start, datetime):
        item_start = dates.to_utc(datetime.utcfromtimestamp(item.start))
    else:
        item_start = item.start

    if not isinstance(item.end, datetime):
        item_end = dates.to_utc(datetime.utcfromtimestamp(item.end))
    else:
        item_end = item.end

    if not item.recurrence:

        if not overlaps(min_date, max_date, item_start, item_end):
            return []
        else:
            return [Occurrence(item, item_start, item_end)]

    tz = pytz.timezone(item.timezone)
    local_start = tz.normalize(item_start)

    _occurrences = recurrence_sequence_ical(
        start=local_start,
        recrule=item.recurrence,
        from_=min_date,
        until=max_date
    )

    result = []
    duration = item_end - item_start

    for start in _occurrences:
        start = utcoffset_normalize(start, dstmode=DSTADJUST)
        result.append(Occurrence(item, start, start + duration))

    return result


def has_future_occurrences(item, reference_date):

    if not item.recurrence:
        return reference_date <= item.start

    futures = recurrence_sequence_ical(
        item.start, recrule=item.recurrence, from_=reference_date
    )

    try:
        return bool(futures.next())
    except StopIteration:
        return False
