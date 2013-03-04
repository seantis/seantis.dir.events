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
from Products.CMFCore.utils import getToolByName
from plone.namedfile import NamedFile, NamedImage
from plone.dexterity.utils import createContentInContainer
from zope.interface import alsoProvides

from collective import noindexing

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

    def disable_indexing(self):
        self.context._v_fetching = True
        noindexing.patches.apply()

    def enable_indexing(self):
        self.context._v_fetching = False
        noindexing.patches.unapply()

    def fetch(self, source, function, limit=None):

        start = datetime.now()
        log.info('begin fetching events for %s' % source)

        self.disable_indexing()

        try:
            imported = self._fetch(source, function, limit)
        finally:
            self.enable_indexing()

        runtime = datetime.now() - start
        minutes = runtime.total_seconds() // 60
        seconds = runtime.seconds - minutes * 60

        log.info('imported %i events in %i minutes, %i seconds' % (
            imported, minutes, seconds
        ))

    def _fetch(self, source, function, limit=None):

        events = [e for e in function(self.context, self.request)]
        total = len(events) if not limit else limit
        existing = self.groupby_source_id(self.existing_events(source))

        workflowTool = getToolByName(self.context, 'portal_workflow')

        categories = dict(cat1=set(), cat2=set())

        for ix, event in enumerate(events):

            # keep a set of all categories for the suggestions
            for cat in categories:
                categories[cat] |= event[cat]

            # for testing
            if limit and (ix + 1) > limit:
                log.info('reached limit of %i events' % limit)
                break

            # flush to disk every 500th event to keep memory usage low
            if (ix + 1) % 500 == 0:
                transaction.savepoint(True)

            log.info('importing %i/%i %s @ %s' % (
                ix + 1, total, event['title'],
                event['start'].strftime('%d.%m.%Y %H:%M')
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

            def allow_download(download, url):

                if download != 'image':
                    return True

                # whitelist the images that are known to work
                # not working is *.bmp. We could convert but I'd rather
                # force people to use a sane format
                return url.lower().endswith(('png', 'jpg', 'jpeg'))

            for download, method in downloads.items():
                url = event.get(download)

                if not url or not allow_download(download, url):
                    event[download] = None
                else:
                    event[download] = method(self.download(url))

            # latitude and longitude are set through the interface
            lat, lon = event.get('latitude'), event.get('longitude')

            if lat:
                del event['latitude']

            if lon:
                del event['longitude']

            obj = createContentInContainer(
                self.context, 'seantis.dir.events.item',
                checkConstraints=False,
                **event
            )

            # set coordinates now
            if lat and lon:
                IWriteGeoreferenced(obj).setGeoInterface(
                    'Point', map(float, (lon, lat))
                )

            workflowTool.doActionFor(obj, 'submit')
            workflowTool.doActionFor(obj, 'publish')

            for download in downloads:
                getattr(obj, download)

            alsoProvides(obj, IExternalEvent)

        # add categories to suggestions
        for category in categories:
            key = '%s_suggestions' % category
            existing = set(getattr(self.context, key))
            new = categories[category] | existing

            setattr(self.context, key, sorted(new))

        log.info('committing events for %s' % source)
        transaction.commit()

        return ix + 1  # number of imported events

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

        indexurl = self.context.absolute_url() + '/eventindex?rebuild&reindex'
        log.info('redirecting to %s for index regeneration' % indexurl)
        self.request.response.redirect(indexurl)
