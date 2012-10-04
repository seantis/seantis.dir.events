from five import grok

from seantis.dir.base.catalog import DirectoryCatalog
from seantis.dir.base.interfaces import IDirectoryCatalog

from seantis.dir.events import utils
from seantis.dir.events.recurrence import occurrences
from seantis.dir.events.directory import IEventsDirectory

class EventsDirectoryCatalog(DirectoryCatalog):

    grok.context(IEventsDirectory)
    grok.provides(IDirectoryCatalog)

    def __init__(self, *args, **kwargs):
        self.start, self.end = utils.event_range()
        super(EventsDirectoryCatalog, self).__init__(*args, **kwargs)

    def sortkey(self):
        return lambda i: i.start

    def spawn(self, realitems):
        for item in realitems:
            for occurrence in occurrences(item, self.start, self.end):
                yield occurrence

    def items(self):
        real = super(EventsDirectoryCatalog, self).items()
        return list(self.spawn(real))

    def filter(self, term):
        real = super(EventsDirectoryCatalog, self).filter(term)
        return list(self.spawn(real))

    def search(self, text):
        real = super(EventsDirectoryCatalog, self).search(text)
        return list(self.spawn(real))    