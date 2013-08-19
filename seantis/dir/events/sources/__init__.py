import logging
log = logging.getLogger('seantis.dir.events')

import hashlib
import inspect
import transaction
import isodate
import pytz

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
from zope.annotation.interfaces import IAnnotations

from seantis.dir.base.interfaces import (
    IDirectoryCatalog,
    IDirectoryCategorized
)
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

    def enable_indexing(self):
        self.context._v_fetching = False

    def fetch(
        self, source, function, limit=None, reimport=False, source_ids=[]
    ):

        start = datetime.now()
        log.info('begin fetching events for %s' % source)

        self.disable_indexing()

        try:
            imported = self._fetch(
                source, function, limit, reimport, source_ids
            )
        finally:
            self.enable_indexing()

        log.info('reindexing commited events')

        # reindex in the ZCatalog
        for event in imported:
            event.reindexObject()

        self.context.reindexObject()

        # reindex in the Events Catalog
        IDirectoryCatalog(self.context).reindex()

        runtime = datetime.now() - start
        minutes = runtime.total_seconds() // 60
        seconds = runtime.seconds - minutes * 60

        log.info('imported %i events in %i minutes, %i seconds' % (
            len(imported), minutes, seconds
        ))

    def get_last_update_time(self):
        assert self.annotation_key

        isostring = IAnnotations(self.context).get(self.annotation_key, None)

        if not isostring:
            return None
        else:
            return isodate.parse_datetime(isostring)

    def set_last_update_time(self, dt):
        assert self.annotation_key

        assert isinstance(dt, datetime)
        assert dt.tzinfo, "please use a timezone aware datetime"

        # use string to store date to ensure that the annotation
        # doesn't cause problems in the future
        annotations = IAnnotations(self.context)
        annotations[self.annotation_key] = isodate.datetime_isoformat(dt)

    def _fetch(
        self, source, function, limit=None, reimport=False, source_ids=[]
    ):

        events = sorted(
            function(self.context, self.request),
            key=lambda e: (e['last_update'], e['source_id'])
        )

        fetch_ids = set(event['fetch_id'] for event in events)
        assert len(fetch_ids) == 1, """
            Each event needs a fetch_id which describes the id of the
            whole fetch process and is therefore the same for all events
            in a single fetch. See seantis.dir.events.source.guidle:events
        """

        self.annotation_key = hashlib.sha1(list(fetch_ids)[0]).hexdigest()
        last_update = self.get_last_update_time()
        last_update_in_run = datetime.min.replace(tzinfo=pytz.timezone('utc'))

        if not last_update:
            log.info('initial import')
            changed_offers_only = False
        elif reimport:
            log.info('reimport everything')
            changed_offers_only = False
        else:
            log.info('importing updates since {}'.format(last_update))
            changed_offers_only = True

        total = len(events) if not limit else limit
        existing = self.groupby_source_id(self.existing_events(source))

        workflowTool = getToolByName(self.context, 'portal_workflow')

        categories = dict(cat1=set(), cat2=set())
        imported = []

        limit_reached_id = None

        for ix, event in enumerate(events):

            if limit_reached_id and limit_reached_id != event['source_id']:
                break

            if source_ids and event['source_id'] not in source_ids:
                continue

            assert 'last_update' in event, """
                Each event needs a last_update datetime info which is used
                to determine if any changes were done. This is used for
                importing only changed events.
            """

            if last_update_in_run < event['last_update']:
                last_update_in_run = event['last_update']

            if changed_offers_only and event['source_id'] in existing:
                if event['last_update'] <= last_update:
                    log.info('skipping %s @ %s' % (
                        event['title'],
                        event['start'].strftime('%d.%m.%Y %H:%M')
                    ))
                    continue

            # keep a set of all categories for the suggestions
            for cat in categories:
                categories[cat] |= event[cat]

            # for testing
            if limit and len(imported) > limit and not limit_reached_id:
                log.info('reached limit of %i events' % limit)
                # don't quit right away, all events of the same source_id
                # need to be imported first since they have the same
                # update_time
                limit_reached_id = event['source_id']

            # flush to disk every 500th event to keep memory usage low
            if len(imported) % 500 == 0:
                transaction.savepoint(True)

            log.info('importing %i/%i %s @ %s' % (
                len(imported), total, event['title'],
                event['start'].strftime('%d.%m.%Y %H:%M')
            ))

            event['source'] = source

            # source id's are not necessarily unique as a single external
            # event might have to be represented as more than one event in
            # seantis.dir.events - therefore updating is done through
            # deleting first, adding second

            if event['source_id'] in existing:
                for e in existing[event['source_id']]:
                    self.context._delObject(e.id, suppress_events=True)
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

            # so are categories
            cats = map(event.get, ('cat1', 'cat2'))
            del event['cat1']
            del event['cat2']

            assert 'cat3' not in event and 'cat4' not in event, """
                unsupported categories
            """

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

            # followed by the categories
            IDirectoryCategorized(obj).cat1 = list(cats[0])
            IDirectoryCategorized(obj).cat2 = list(cats[1])

            workflowTool.doActionFor(obj, 'submit')
            workflowTool.doActionFor(obj, 'publish')

            for download in downloads:
                getattr(obj, download)

            alsoProvides(obj, IExternalEvent)
            imported.append(obj)

        self.set_last_update_time(last_update_in_run)

        # add categories to suggestions
        for category in categories:
            key = '%s_suggestions' % category
            existing = set(getattr(self.context, key))
            new = categories[category] | existing

            setattr(self.context, key, sorted(new))

        log.info('committing events for %s' % source)
        transaction.commit()

        return imported

    def existing_events(self, source):

        catalog = getToolByName(self.context, 'portal_catalog')
        candidates = catalog(object_provides=IExternalEvent.__identifier__)

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

        limit = int(self.request.get('limit', 0))
        reimport = bool(self.request.get('reimport', False))
        ids = self.request.get('source-ids', '').split(',')

        self.source = source
        self.fetch(
            source, sources[source], limit, reimport, all(ids) and ids or None
        )

        IDirectoryCatalog(self.context).reindex()
