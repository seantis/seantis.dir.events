from pytz import timezone
from datetime import datetime, timedelta

from zope.proxy import ProxyBase
from dateutil.rrule import rrulestr
from urllib import urlencode

from plone.event.utils import utcoffset_normalize, DSTADJUST

from seantis.dir.events import dates
from seantis.dir.events.dates import overlaps

# plone.app.event creates occurrences using adapters, which seems a bit wasteful
# to me. It also doesn't play too well with my interfaces (overridding either
# my title/description attributes ore not showing my methods).

# This pure proxy has none of those problems. 

# ========================================================================
# THERE IS ONE CAVEAT. In templates "context/start" will yield the wrapped
# item's start. "python: context.start" on the other hand will yield the
# occurence's start. Same with other properties/methods
# ========================================================================
class Occurrence(ProxyBase):

    __slots__ = ('_wrapped', '_start', '_end')

    def __init__(self, item, start, end):
        self._wrapped = item
        self._start = start
        self._end = end

    def __new__(cls, item, start, end):
        return ProxyBase.__new__(cls, item)

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

    def human_daterange(self):
        # occurrences split to days all get the same date string
        if not self.recurrence and (self._end - self._start).days > 0:
            start = self._wrapped.start
            end = self._wrapped.end
        else:
            start = self._start
            end = self._end

        start = self.tz.normalize(start)
        end = self.tz.normalize(end)
        
        return dates.human_daterange(start, end)


def pick_occurrence(item, start):
    """ Returns the occurrence at startdate. This suffices because two
    occurrences of the same item are never on the same day. 

    """

    min_date = datetime(start.year, start.month, start.day, 
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
    
    days = (occurrence.end - occurrence.start).days

    if days == 0:
        yield occurrence
    else:
        for day in xrange(0, days+1):
            first_day = day == 0
            last_day = day == days

            if first_day:
                start = occurrence.start
            else:
                start = datetime(
                    occurrence.start.year,
                    occurrence.start.month,
                    occurrence.start.day,
                    tzinfo=occurrence.start.tzinfo
                ) + timedelta(days=day)

            if last_day:
                end = occurrence.end
            else:
                end = datetime(
                    occurrence.start.year,
                    occurrence.start.month,
                    occurrence.start.day,
                    tzinfo=occurrence.start.tzinfo
                ) + timedelta(days=day+1, microseconds=-1)

            # if the given occurrence is already a proxy, don't double-wrap it
            if isinstance(occurrence, Occurrence):
                yield Occurrence(occurrence._wrapped, start, end)
            else:
                yield Occurrence(occurrence, start, end)

def occurrences(item, min_date, max_date):
    """ Returns the occurrences for item between min and max date.
    Will return a list with a single item if the given item has no recurrence.

    """

    if not item.recurrence:

        if not overlaps(min_date, max_date, item.start, item.end):
            return []
        else:
            return [Occurrence(item, item.start, item.end)]
    
    duration = item.end - item.start

    # plone.app.event doesn't seem to store the timezone info on the
    # rrule string when the user selects an end-date for a recurrence.
    # Those dates should have the timezone of the item and the following
    # function called by dateutil will resolve that issue.
    def get_timezone(name, offset):
        if not name and not offset:
            return item.timezone
    
    result = []
    rrule = rrulestr(item.recurrence, dtstart=item.local_start, tzinfos=get_timezone)

    for start in rrule.between(min_date, max_date, inc=True):
        start = utcoffset_normalize(start, dstmode=DSTADJUST)
        result.append(Occurrence(item, start, start + duration))

    return result