import threading

from datetime import datetime
from five import grok

from itertools import ifilter
from plone.app.event.ical import construct_calendar
from plone.memoize import instance

from seantis.dir.base.catalog import DirectoryCatalog
from seantis.dir.base.interfaces import IDirectoryCatalog

from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events.interfaces import (
    IEventsDirectory, IEventsDirectoryItem
)

from blist import sortedset


class EventsDirectoryIndex(object):

    def __init__(self):
        self.index = sortedset()
        self.lock = threading.Lock()

    def event_identity(self, event):
        date = dates.delete_timezone(event.start)
        return date.strftime('%Y.%m.%d-%H:%M') + ';' + event.id

    def event_by_identity(self, identity):
        date, id = identity.split(';')
        date = dates.to_utc(datetime.strptime('%Y.%m.%d-%H:%M', date))

        real = self.get_object(
            self.catalog(id=id, path={'query': self.path, 'depth': 1})
        )

        items = self.spawn((real,), date, date)
        assert len(items) == 1

        return items[0]

    def index_all_events(self, catalog, reindex=False):
        if not reindex and self.index:
            return

        with self.lock:
            start, end = map(dates.to_utc, dates.eventrange())

            real = super(EventsDirectoryCatalog, catalog).items()

            for event in catalog.spawn(real, start, end):
                self.index.add(self.event_identity(event))

    def index_event(self, event):
        with self.lock:
            self.index.add(self.event_identity(event))

    def unindex_event(self, event):
        with self.lock:
            self.index.remove(self.event_identity(event))


_eventindex = EventsDirectoryIndex()


class EventsDirectoryCatalog(DirectoryCatalog):

    grok.context(IEventsDirectory)
    grok.provides(IDirectoryCatalog)

    def __init__(self, *args, **kwargs):
        self._daterange = dates.default_daterange
        self._states = ('submitted', 'published')
        super(EventsDirectoryCatalog, self).__init__(*args, **kwargs)

        _eventindex.index_all_events(self)

    @property
    def eventindex(self):
        return _eventindex

    @property
    def submitted_count(self):
        """ Returns the submitted count depending on the current date filter
        but independent of the current states filter.

        This needs to loop through all elements again so use only if needed.
        """

        results = self.catalog(path={'query': self.path, 'depth': 1},
            object_provides=IEventsDirectoryItem.__identifier__,
            review_state=('submitted', )
        )

        submitted_count = 0

        items = []
        for item in map(self.get_object, results):
            if item.allow_action('publish'):
                items.append(item)

        for spawn in self.spawn(items):
            submitted_count += 1

        return submitted_count

    def get_daterange(self):
        return self._daterange

    @instance.clearafter
    def set_daterange(self, range):
        assert dates.is_valid_daterange(range), "invalid date range %s" % range
        self._daterange = range

    daterange = property(get_daterange, set_daterange)

    def get_states(self):
        return self._states

    @instance.clearafter
    def set_states(self, states):
        for state in states:
            # as an added security measure it is not yet possible to
            # query for previewed events as they should only be availble
            # to the user with the right token (see form.py)
            assert state in ('submitted', 'published', 'archived')

        self._states = states

    states = property(get_states, set_states)

    def sortkey(self):
        return lambda i: i.start

    def query(self, **kwargs):
        results = self.catalog(path={'query': self.path, 'depth': 1},
            object_provides=IEventsDirectoryItem.__identifier__,
            review_state=self._states,
            **kwargs
        )
        return results

    def spawn(self, realitems, start=None, end=None):
        if not all((start, end)):
            start, end = getattr(dates.DateRanges(), self._daterange)

        for item in realitems:
            for occurrence in recurrence.occurrences(item, start, end):
                for split in recurrence.split_days(occurrence):
                    if dates.overlaps(start, end, split.start, split.end):
                        yield split

    def hide_blocked(self, realitems):
        """ Returns a generator filtering real items, with the submitted items
        which the user can see but not publish left out.

        As this could be reeealy slow we do a bit of a shortcut by only
        checking for the publish action right on the item. The guard is
        in place anyway, so the user will at worst see an item with which
        he can't do anything.

        """

        if not 'submitted' in self.states:
            return (r for r in realitems)

        key = lambda i: i.state != 'submitted' or i.allow_action('publish')
        return ifilter(key, realitems)

    @instance.memoize
    def items(self):
        real = super(EventsDirectoryCatalog, self).items()
        return sorted(self.spawn(self.hide_blocked(real)), key=self.sortkey())

    def filter(self, term):
        nonempty_terms = [t for t in term.values() if t != u'!empty']

        if len(nonempty_terms) == 0:
            return self.items()

        real = super(EventsDirectoryCatalog, self).filter(term)
        return sorted(self.spawn(self.hide_blocked(real)), key=self.sortkey())

    @instance.memoize
    def search(self, text):
        real = super(EventsDirectoryCatalog, self).search(text)
        return sorted(self.spawn(self.hide_blocked(real)), key=self.sortkey())

    def calendar(self, search=None, filter=None):
        if search:
            items = super(EventsDirectoryCatalog, self).search(search)
        elif filter:
            items = super(EventsDirectoryCatalog, self).filter(filter)
        else:
            items = super(EventsDirectoryCatalog, self).items()

        return construct_calendar(self.directory, items)
