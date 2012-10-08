from five import grok

from seantis.dir.base.catalog import DirectoryCatalog
from seantis.dir.base.interfaces import IDirectoryCatalog

from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events.directory import IEventsDirectory

class EventsDirectoryCatalog(DirectoryCatalog):

    grok.context(IEventsDirectory)
    grok.provides(IDirectoryCatalog)

    def __init__(self, *args, **kwargs):
        self._daterange = 'this_month'
        self.start, self.end = dates.eventrange()
        super(EventsDirectoryCatalog, self).__init__(*args, **kwargs)

    @property
    def daterange(self):
        return self._daterange

    @daterange.setter
    def daterange(self, range):
        assert dates.is_valid_daterange(range), "invalid date range %s" % range
        self._daterange = range

    def sortkey(self):
        return lambda i: i.start

    def spawn(self, realitems):
        self.start, self.end = getattr(dates.DateRanges(), self._daterange)

        for item in realitems:
            for occurrence in recurrence.occurrences(item, self.start, self.end):
                for split in recurrence.split_days(occurrence):
                    yield split

    def items(self):
        real = super(EventsDirectoryCatalog, self).items()
        return sorted(self.spawn(real), key=self.sortkey())

    def filter(self, term):
        real = super(EventsDirectoryCatalog, self).filter(term)
        return sorted(self.spawn(real), key=self.sortkey())

    def search(self, text):
        real = super(EventsDirectoryCatalog, self).search(text)
        return sorted(self.spawn(real), key=self.sortkey())