import logging
log = logging.getLogger('seantis.dir.events')

import hashlib
import transaction
import isodate
import pytz

from functools32 import lru_cache

from five import grok

from datetime import datetime, timedelta
from urllib2 import urlopen, HTTPError
from itertools import groupby
from random import shuffle
from threading import Lock
from plone.synchronize import synchronized

from zope.component.hooks import getSite

from collective.geo.geographer.interfaces import IWriteGeoreferenced
from Products.CMFCore.utils import getToolByName
from plone.namedfile import NamedFile, NamedImage
from plone.dexterity.utils import createContentInContainer
from zope.interface import alsoProvides
from zope.annotation.interfaces import IAnnotations

from seantis.dir.base import directory
from seantis.dir.base.interfaces import (
    IDirectoryCatalog,
    IDirectoryCategorized
)
from seantis.dir.events.interfaces import (
    IExternalEvent,
    IExternalEventCollector,
    IExternalEventSource,
    IEventsDirectory,
    NoImportDataException
)
from seantis.dir.events.unrestricted import execute_under_special_role


class ExternalEventImporter(object):

    def __init__(self, context):
        self.context = context

    def sources(self):
        result = []
        sources = IDirectoryCatalog(self.context).catalog(
            object_provides=IExternalEventSource.__identifier__
        )
        for source in sources:
            if source.getObject().enabled:
                result.append(source)

        return result

    @lru_cache(maxsize=50)
    def download(self, url):
        return urlopen(url, timeout=60).read()

    def disable_indexing(self):
        self.context._v_fetching = True

    def enable_indexing(self):
        self.context._v_fetching = False

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

    def existing_events(self, source):

        catalog = getToolByName(self.context, 'portal_catalog')
        brains = catalog(
            object_provides=IExternalEvent.__identifier__, source=source
        )

        events = [brain.getObject() for brain in brains]

        return events

    def groupby_source_id(self, events):

        ids = {}

        keyfn = lambda e: e.source_id
        events.sort(key=keyfn)

        for key, items in groupby(events, lambda e: e.source_id):
            ids[key] = [e for e in items]

        return ids

    def _fetch_one(
        self, source, function, limit=None, reimport=False, source_ids=[],
        autoremove=False
    ):
        imported = []

        try:
            events = sorted(
                function(),
                key=lambda e: (e['last_update'], e['source_id'])
            )
        except NoImportDataException:
            log.info('no data received for %s' % source)
            return imported

        existing = self.groupby_source_id(self.existing_events(source))

        # Autoremove externally deleted events
        if autoremove:
            new_ids = [event['source_id'] for event in events]
            old_ids = existing.keys()
            delta = list(set(old_ids) - set(new_ids))
            if limit is not None:
                delta = delta[:limit]
            for rm_id in delta:
                # source id's are not necessarily unique
                for event in existing[rm_id]:
                    log.info('Deleting %s @ %s' % (
                        event.title,
                        event.start.strftime('%d.%m.%Y %H:%M')
                    ))
                    self.context.manage_delObjects(event.id)

        if len(events) == 0:
            return imported

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

        workflowTool = getToolByName(self.context, 'portal_workflow')

        categories = dict(cat1=set(), cat2=set())

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
                    # log.info('skipping %s @ %s' % (
                    #     event['title'],
                    #     event['start'].strftime('%d.%m.%Y %H:%M')
                    # ))
                    continue

            # keep a set of all categories for the suggestions
            for cat in categories:
                if cat not in event:
                    event[cat] = set()
                categories[cat] |= event[cat]

            # stop at limit
            if limit and (len(imported)+1) >= limit and not limit_reached_id:
                log.info('reached limit of %i events' % limit)
                # don't quit right away, all events of the same source_id
                # need to be imported first since they have the same
                # update_time
                limit_reached_id = event['source_id']

            # flush to disk every 500th event to keep memory usage low
            if len(imported) != 0 and len(imported) % 500 == 0:
                transaction.savepoint(True)

            log.info('importing %i/%i %s @ %s' % (
                (len(imported) + 1), total, event['title'],
                event['start'].strftime('%d.%m.%Y %H:%M')
            ))

            event['source'] = source

            # If the existing event has been hidden, we keep it hidden
            hide_event = False
            if event['source_id'] in existing:
                for e in existing[event['source_id']]:
                    hide_event |= e.review_state == 'hidden'

            # source id's are not necessarily unique as a single external
            # event might have to be represented as more than one event in
            # seantis.dir.events - therefore updating is done through
            # deleting first, adding second
            if event['source_id'] in existing:
                for e in existing[event['source_id']]:
                    self.context.manage_delObjects(e.id)
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
                return url.lower().endswith((
                    'png', 'jpg', 'jpeg', '@@images/image'
                ))

            for download, method in downloads.items():
                url = event.get(download)
                name = download + '_name'

                if not url or not allow_download(download, url):
                    event[download] = None
                else:
                    try:
                        event[download] = method(self.download(url))
                        if name in event:
                            event[download].filename = event[name]
                    except HTTPError:
                        event[download] = None

                if name in event:
                    del event[name]

            # latitude and longitude are set through the interface
            lat, lon = event.get('latitude'), event.get('longitude')
            if 'latitude' in event:
                del event['latitude']
            if 'longitude' in event:
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

            if hide_event:
                workflowTool.doActionFor(obj, 'hide')

            imported.append(obj)

        self.set_last_update_time(last_update_in_run)

        # add categories to suggestions
        for category in categories:
            key = '%s_suggestions' % category
            existing = getattr(self.context, key)
            existing = set(existing) if existing is not None else set()
            new = categories[category] | existing

            setattr(self.context, key, sorted(new))

            diff = categories[category] - existing
            if len(diff):
                log.info('added to %s %s' % (category, diff))

        log.info('committing events for %s' % source)
        transaction.commit()

        return imported

    def fetch_one(
        self, source, function, limit=None, reimport=False, source_ids=[],
        autoremove=False
    ):

        start = datetime.now()
        log.info('begin fetching events for %s' % source)

        self.disable_indexing()

        try:
            imported = self._fetch_one(
                source, function, limit, reimport, source_ids, autoremove
            )
        finally:
            self.enable_indexing()

        runtime = datetime.now() - start

        if len(imported):
            # Reindex
            log.info('reindexing commited events for %s' % source)

            for event in imported:
                event.reindexObject()

            self.context.reindexObject()

            IDirectoryCatalog(self.context).reindex()

            # Log runtime
            minutes = runtime.total_seconds() // 60
            seconds = runtime.seconds - minutes * 60
            log.info('imported %i events in %i minutes, %i seconds' % (
                len(imported), minutes, seconds
            ))

        return len(imported)


class ExternalEventImportScheduler(object):

    _lock = Lock()

    def __init__(self):
        self.running = False
        self.last_run = datetime.now()

    @synchronized(_lock)
    def handle_run(self, do_stop=False):
        """Check if we can start importing or signal that we are finished.

        Note that it is possible that requests are still blocked, i.e. when
        doing the same request (e.g. '/fetch'), see ZSever/medusa/http_server.
        
        Note that it happend that some threads died while executing, hence 
        forcing a run every 4 hours.
        """
        return_value = False

        if do_stop:
            self.running = False
            self.last_run = datetime.now()
        else:
            delta = datetime.now() - self.last_run
            if not self.running or delta > timedelta(hours=4):
                self.running = True
                self.last_run = datetime.now()
                return_value = True

        return return_value

    def run(self, context, reimport=False, source_ids=[], no_shuffle=False):

        len_imported = 0
        len_sources = 0

        if not self.handle_run():
            log.info('already importing')
            return len_imported, len_sources

        directory = '/'.join(context.getPhysicalPath())
        log.info('begin importing sources from %s' % (directory))

        try:
            importer = ExternalEventImporter(context)
            sources = importer.sources()
            if not no_shuffle:
                shuffle(sources)
            for source in sources:
                len_sources += 1
                path = source.getPath()
                events = importer.fetch_one(
                    path,
                    IExternalEventCollector(source.getObject()).fetch,
                    source.getObject().limit,
                    reimport, source_ids,
                    source.getObject().autoremove)
                log.info('source %s processed' % (path))
                len_imported += events
        finally:
            context.reindexObject()
            IDirectoryCatalog(context).reindex()
            log.info('importing sources from %s finished' % (directory))
            self.handle_run(True)

        return len_imported, len_sources


import_scheduler = ExternalEventImportScheduler()


class EventsDirectoryFetchView(grok.View, directory.DirectoryCatalogMixin):

    grok.name('fetch')
    grok.context(IEventsDirectory)

    template = None

    def render(self):

        self.request.response.setHeader("Content-type", "text/plain")

        reimport = bool(self.request.get('reimport', False))
        ids = self.request.get('source-ids', '').split(',')
        no_shuffle = bool(self.request.get('no_shuffle', False))
        do_run = self.request.get('run') == '1'

        if do_run:
            imported, sources = execute_under_special_role(
                getSite(), 'Manager',
                import_scheduler.run, self.context, reimport,
                all(ids) and ids or None, no_shuffle
            )

            return u'%i events imported from %i sources' % (imported, sources)

        else:
            return u''
