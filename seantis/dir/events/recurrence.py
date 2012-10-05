from datetime import datetime, timedelta

from zope.proxy import ProxyBase
from dateutil.rrule import rrulestr
from urllib import urlencode

from seantis.dir.events.utils import overlaps, to_utc

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

def occurrence(item, start):
    """ Returns the occurrence at startdate. This suffices because two
    occurrences of the same item are never on the same day. """

    min_date = datetime(start.year, start.month, start.day, 
        tzinfo=item.start.tzinfo
    )
    max_date = min_date + timedelta(days=1, microseconds=-1)

    found = occurrences(item, min_date, max_date)    
    assert len(found) in (0, 1), "Multiple occurences on the same day?"

    return found and found[0] or None
    

def occurrences(item, min_date, max_date):

    if not item.recurrence:

        if not overlaps(min_date, max_date, to_utc(item.start), to_utc(item.end)):
            return []
        else:
            return [Occurrence(item, item.start, item.end)]
    
    duration = item.end - item.start
    
    result = []
    rrule = rrulestr(item.recurrence, dtstart=item.start)

    for start in rrule.between(min_date, max_date, inc=True):
        result.append(Occurrence(item, start, start + duration))

    return result