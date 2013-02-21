from datetime import datetime
from five import grok

from itertools import ifilter
from plone.app.event.ical import construct_calendar
from plone.memoize import instance

from zope.annotation.interfaces import IAnnotations
from zope.app.container.interfaces import IObjectMovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from Products.CMFCore.interfaces import IActionSucceededEvent

from seantis.dir.base.catalog import DirectoryCatalog
from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.base.utils import cached_property

from seantis.dir.events import utils
from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events.interfaces import (
    IEventsDirectory, IEventsDirectoryItem
)

from blist import sortedset


def reindex(item, directory):

    if not IEventsDirectory.providedBy(directory):
        return

    if not IEventsDirectoryItem.providedBy(item):
        return

    if item and directory:
        catalog = utils.get_catalog(directory)
        catalog.reindex([item])


@grok.subscribe(IEventsDirectoryItem, IObjectMovedEvent)
def onMovedItem(item, event):
    reindex(item, event.oldParent)
    reindex(item, event.newParent)


@grok.subscribe(IEventsDirectoryItem, IObjectModifiedEvent)
def onModifiedItem(item, event):
    reindex(item, item.get_parent())


@grok.subscribe(IEventsDirectoryItem, IActionSucceededEvent)
def onChangedWorkflowState(item, event):
    reindex(item, item.get_parent())


class LazyList(object):

    def __init__(self, get_item, length):
        assert callable(get_item)

        self._get_item = get_item
        self.length = length
        self.cache = [get_item] * length

    def get_item(self, index):
        if self.cache[index] == self._get_item:
            self.cache[index] = self.cache[index](index)

        return self.cache[index]

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        if isinstance(key, slice):
            return map(self.get_item, range(*key.indices(self.length)))

        if (key + 1) > self.length:
            raise IndexError

        return self.get_item(key)


class EventIndex(object):

    def __init__(self, catalog):
        self.catalog = catalog
        self.key = 'seantis.dir.events.eventindex'
        self.datekey = '%Y.%m.%d'

        if not self.index:
            self.reindex()

    @property
    def name(self):
        raise NotImplementedError

    def update(self, events):
        raise NotImplementedError

    def remove(self, events):
        raise NotImplementedError

    def reindex(self, events=[]):
        raise NotImplementedError

    @property
    def annotations(self):
        return IAnnotations(self.catalog.directory, self.key)

    def get_index(self):
        return self.annotations.get(self.name, None)

    def set_index(self, value):
        self.annotations[self.name] = value

    index = property(get_index, set_index)

    def real_event(self, id):
        return self.catalog.query(id=id)[0].getObject()

    def real_events(self):
        return super(EventsDirectoryCatalog, self.catalog).items()

    def spawn_events(self, real, start=None, end=None):

        if not start or not end:
            start, end = map(dates.to_utc, dates.eventrange())

        return self.catalog.spawn(real, start, end)

    def event_identity(self, event):
        date = dates.delete_timezone(event.start)
        return '%s;%s;%s' % (
            event.review_state, date.strftime(self.datekey), event.id
        )

    def event_identity_data(self, identity):
        state, date, id = identity.split(';')
        date = dates.to_utc(datetime.strptime(date, self.datekey))

        return state, date, id

    def event_by_identity(self, identity):
        state, date, id = self.event_identity_data(identity)

        ranges = dates.DateRanges(
            now=dates.as_timezone(date, dates.default_timezone())
        )
        start, end = ranges.today
        start = start.replace(hour=0)

        items = list(self.spawn_events([self.real_event(id)], start, end))

        assert len(items) == 1
        assert items[0].review_state == state, 'stale index'

        return items[0]


class EventOrderIndex(EventIndex):

    name = 'eventorder'

    def reindex(self, events=[]):
        if not events:
            events = self.real_events()
            self.index = sortedset()

        self.update(events)

    def update(self, events):
        self.remove(events)

        for event in self.spawn_events(events):
            if event.review_state == 'published':
                self.index.add(self.event_identity(event))

    def remove(self, events):
        stale = set()

        for real in events:
            end = ';%s' % real.id

            for identity in self.index:
                if identity.endswith(end):
                    stale.add(identity)

        self.index = sortedset(self.index - stale)

    def by_range(self, start, end):

        if not start and not end:
            return self.index

        start = start and dates.delete_timezone(start) or datetime.min
        end = end and dates.delete_timezone(end) or datetime.max
        start = start.date()
        end = end.date()

        def between_start_and_end(identity):
            date = dates.delete_timezone(
                self.event_identity_data(identity)[1]
            ).date()
            return dates.overlaps(start, end, date, date)

        return filter(between_start_and_end, self.index)

    def lazy_list(self, start, end):
        subset = self.by_range(start, end)
        get_item = lambda i: self.event_by_identity(subset[i])
        return LazyList(get_item, len(subset))


class EventsDirectoryCatalog(DirectoryCatalog):

    grok.context(IEventsDirectory)
    grok.provides(IDirectoryCatalog)

    def __init__(self, *args, **kwargs):
        self._daterange = dates.default_daterange
        self._states = ('published', )
        super(EventsDirectoryCatalog, self).__init__(*args, **kwargs)

    def reindex(self, events=[]):
        for index in (self.orderindex, ):
            index.reindex(events)

    @cached_property
    def orderindex(self):
        return EventOrderIndex(self)

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
        for item in results:
            if self.directory.allow_action('publish', item):
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

        key = lambda i: i.review_state != 'submitted' \
                     or self.directory.allow_action('publish', i)

        return ifilter(key, realitems)

    @property
    def lazy_list(self):
        if list(self.states) == ['published']:
            start, end = getattr(dates.DateRanges(), self.daterange)
            return self.orderindex.lazy_list(start, end)
        else:
            return self.items()

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
