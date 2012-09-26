from zope.proxy import ProxyBase
from dateutil.rrule import rrulestr, rruleset

from seantis.dir.events.utils import overlaps, to_utc

# plone.app.event creates occurrences using adapters, which seems a bit wasteful
# to me. It also doesn't play too well with my interfaces (overridding either
# my title/description attributes ore not showing my methods).

# This pure proxy has none of those problems. 
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