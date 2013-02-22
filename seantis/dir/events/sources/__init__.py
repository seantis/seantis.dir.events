import logging
log = logging.getLogger('seantis.dir.events')

import inspect
import transaction

from functools32 import lru_cache

from datetime import datetime
from urllib import urlopen
from itertools import groupby

from five import grok

from collective.geo.geographer.interfaces import IWriteGeoreferenced
from plone.namedfile import NamedFile, NamedImage
from plone.dexterity.utils import createContentInContainer
from zope.interface import alsoProvides

from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.base.directory import DirectoryCatalogMixin
from seantis.dir.events.interfaces import (
    IEventsDirectory,
    IExternalEvent
)


signature_method = 'fetch_events'


def available_sources():
    """ Search through the available modules of seantis.dir.events.sources
    and make available the ones which implement the signature_method.

    The result is a dictionary (name of source => function).

    """

    from seantis.dir.events import sources

    callables = {}

    for name, module in inspect.getmembers(sources, inspect.ismodule):
        functions = dict(inspect.getmembers(module, inspect.isfunction))

        if signature_method in functions:
            callables[name] = functions[signature_method]

    return callables


class FetchView(grok.View, DirectoryCatalogMixin):

    grok.name('fetch')
    grok.context(IEventsDirectory)
    grok.require('cmf.ManagePortal')

    @lru_cache(maxsize=50)
    def download(self, url):
        return urlopen(url).read()

    def fetch(self, source, function, limit=None):

        start = datetime.now()
        log.info('begin fetching events for %s' % source)

        events = [e for e in function(self.context, self.request)]
        total = len(events)
        existing = self.groupby_source_id(self.existing_events(source))

        for ix, event in enumerate(events):

            # for testing
            if limit and (ix + 1) > limit:
                log.info('reached limit of %i events' % limit)
                break

            # flush to disk every 1000 events to keep memory usage low
            if (ix + 1) % 1000 == 0:
                transaction.savepoint(True)

            log.info('importing %i/%i %s @ %s' % (ix + 1, total,
                event['title'], event['start'].strftime('%d.%m.%Y %H:%M')
            ))

            event['source'] = source

            # source id's are not necessarily unique as a single external
            # event might have to be represented as more than one event in
            # seantis.dir.events - therefore updating is done through
            # deleting first, adding second

            if event['source_id'] in existing:
                ids = [e.id for e in existing[event['source_id']]]
                self.context.manage_delObjects(ids)
                del existing[event['source_id']]

            # image and attachments are downloaded
            downloads = {
                'image': NamedImage,
                'attachment_1': NamedFile,
                'attachment_2': NamedFile
            }

            for download, method in downloads.items():
                url = event.get(download)

                if url:
                    event[download] = method(self.download(url))
                else:
                    event[download] = None

            # latitude and longitude are set through the interface
            lat, lon = event.get('latitude'), event.get('longitude')

            if lat:
                del event['latitude']

            if lon:
                del event['longitude']

            obj = createContentInContainer(
                self.context, 'seantis.dir.events.item', **event
            )

            # set coordinates now
            if lat and lon:
                IWriteGeoreferenced(obj).setGeoInterface(
                    'Point', map(float, (lon, lat))
                )

            obj.submit()
            obj.publish()

            alsoProvides(obj, IExternalEvent)

        log.info('committing events for %s' % source)
        transaction.commit()

        log.info('reindexing ZCatalog')
        self.catalog.catalog.refreshCatalog(clear=1)

        log.info('reindexing event indices')
        self.catalog.reindex()

        runtime = datetime.now() - start
        minutes = runtime.total_seconds() // 60
        seconds = runtime.seconds - minutes * 60
        log.info('imported %i events in %i minutes, %i seconds' % (
            ix + 1, minutes, seconds
        ))

    def existing_events(self, source):

        catalog = IDirectoryCatalog(self.context)
        query = catalog.catalog

        candidates = query(
            path={'query': self.context.getPhysicalPath(), 'depth': 2},
            object_provides=IExternalEvent.__identifier__
        )

        events = []
        for obj in (c.getObject() for c in candidates):
            if obj.source == source:
                events.append(obj)

        return events

    def groupby_source_id(self, events):

        ids = {}

        keyfn = lambda e: e.source_id
        events.sort(key=keyfn)

        for key, items in groupby(events, lambda e: e.source_id):
            ids[key] = [e for e in items]

        return ids

    def render(self):
        source = self.request.get('source')
        sources = available_sources()

        assert source in sources

        self.source = source
        self.fetch(source, sources[source], int(self.request.get('limit', 0)))
