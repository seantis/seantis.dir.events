from five import grok

from seantis.dir.base.catalog import DirectoryCatalog
from seantis.dir.base.interfaces import IDirectoryCatalog

from seantis.dir.events import dates
from seantis.dir.events.recurrence import occurrences
from seantis.dir.events.directory import IEventsDirectory

class EventsDirectoryCatalog(DirectoryCatalog):

    grok.context(IEventsDirectory)
    grok.provides(IDirectoryCatalog)

    def __init__(self, *args, **kwargs):
        self.filter_method = 'is_this_month'
        self.start, self.end = dates.event_range()
        super(EventsDirectoryCatalog, self).__init__(*args, **kwargs)

    @property
    def filter_method(self):
        return self._filter_method

    @filter_method.setter
    def filter_method(self, method):
        assert dates.is_valid_method(method), "invalid filter method %s" % method
        self._filter_method = method

    def sortkey(self):
        return lambda i: i.start

    def spawn(self, realitems):
        is_match = dates.filter_key(self.filter_method)
        for item in realitems:
            for occurrence in occurrences(item, self.start, self.end):
                if is_match(occurrence):
                    yield occurrence

    def items(self):
        real = super(EventsDirectoryCatalog, self).items()
        return sorted(self.spawn(real), key=self.sortkey())

    def filter(self, term):
        real = super(EventsDirectoryCatalog, self).filter(term)
        return sorted(self.spawn(real), key=self.sortkey())

    def search(self, text):
        real = super(EventsDirectoryCatalog, self).search(text)
        return sorted(self.spawn(real), key=self.sortkey())