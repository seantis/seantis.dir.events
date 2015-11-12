import os

from datetime import datetime, timedelta
from five import grok
from logging import getLogger
from plone.protect import createToken
from plone.synchronize import synchronized
from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.events.dates import to_utc
from seantis.dir.events.interfaces import (
    IEventsDirectoryItem, IEventsDirectory, IExternalEvent
)
from seantis.dir.events.recurrence import has_future_occurrences
from seantis.plonetools import unrestricted
from threading import Lock

log = getLogger('seantis.dir.events')


class CleanupScheduler(object):

    _lock = Lock()

    def __init__(self):
        self.next_run = 0

    def is_cleaning_instance(self):
        """ Check if we are the instance which cleans up events.

        This is defined with an environment variable via the buildout file.
        """
        return os.getenv('seantis_events_cleanup', False) == 'true'

    def get_next_run(self, now=None):
        if now is None:
            now = datetime.now()

        # Schedule next run tomorrow at 0:30
        days = 1
        if now.hour < 1 and now.minute < 30:
            days = 0
        next_run = datetime(now.year, now.month, now.day) + timedelta(
            days=days, minutes=30)
        return next_run

    @synchronized(_lock)
    def run(self, directory, dryrun=False, force_run=False, now=None):

        if now is None:
            now = datetime.now()

        if not self.is_cleaning_instance():
            return

        if not self.next_run:
            self.next_run = self.get_next_run(now)

        if (now > self.next_run) or force_run:
            self.next_run = self.get_next_run(now)
            self.cleanup_directory(directory, dryrun=dryrun)

    def remove_stale_previews(self, directory, dryrun=False):

        catalog = IDirectoryCatalog(directory)
        query = catalog.catalog.unrestrictedSearchResults

        log.info('searching for stale previews (> 2 days old)')

        past = to_utc(datetime.utcnow() - timedelta(days=2))
        stale_previews = query(
            path={'query': directory.getPhysicalPath(), 'depth': 2},
            object_provides=IEventsDirectoryItem.__identifier__,
            review_state=('preview'),
            modified={'query': past, 'range': 'max'}
        )
        stale_previews = [p.id for p in stale_previews]

        if stale_previews:
            log.info('deleting stale previews -> %s' % str(stale_previews))
            if not dryrun:
                directory.manage_delObjects(stale_previews)
        else:
            log.info('no stale previews found')

        return stale_previews

    def archive_past_events(self, directory, dryrun=False):

        catalog = IDirectoryCatalog(directory)
        query = catalog.catalog

        log.info('archiving past events (> 2 days old)')

        # events are in the past if they have been over for two days
        # (not one, to ensure that they are really over in all timezones)
        past = to_utc(datetime.utcnow() - timedelta(days=2))
        published_events = query(
            path={'query': directory.getPhysicalPath(), 'depth': 2},
            object_provides=IEventsDirectoryItem.__identifier__,
            review_state=('published', ),
            start={'query': past, 'range': 'max'},
            end={'query': past, 'range': 'max'}
        )

        past_events = []

        for event in published_events:
            event = event.getObject()

            assert event.start < past
            assert event.end < past

            # recurring events may be in the past with one of
            # their occurrences in the future
            if not has_future_occurrences(event, past):
                # published events may be imported events
                if not IExternalEvent.providedBy(event):
                    past_events.append(event)

        ids = [p.id for p in past_events]

        if past_events:
            log.info('archiving past events -> %s' % str(ids))

            if not dryrun:
                for event in past_events:
                    event.archive()
        else:
            log.info('no past events found')

        return ids

    def remove_archived_events(self, directory, dryrun=False):

        catalog = IDirectoryCatalog(directory)
        query = catalog.catalog

        log.info('removing archived events (> 30 days old)')

        past = datetime.utcnow() - timedelta(days=30)
        archived_events = query(
            path={'query': directory.getPhysicalPath(), 'depth': 2},
            object_provides=IEventsDirectoryItem.__identifier__,
            review_state=('archived', ),
            start={'query': past, 'range': 'max'},
            end={'query': past, 'range': 'max'}
        )
        archived_events = [e.id for e in archived_events]

        if archived_events:
            log.info('removing archived events -> %s' % str(archived_events))

            if not dryrun:
                directory.manage_delObjects(archived_events)
        else:
            log.info('no archived events to remove')

        return archived_events

    def remove_past_imported_events(self, directory, dryrun=False):

        catalog = IDirectoryCatalog(directory)
        query = catalog.catalog

        log.info('remove past imported events (> 2 days old)')

        # events are in the past if they have been over for two days
        # (not one, to ensure that they are really over in all timezones)
        past = to_utc(datetime.utcnow() - timedelta(days=2))
        imported_events = query(
            path={'query': directory.getPhysicalPath(), 'depth': 2},
            object_provides=IExternalEvent.__identifier__,
            start={'query': past, 'range': 'max'},
            end={'query': past, 'range': 'max'}
        )

        past_events = []

        for event in imported_events:
            event = event.getObject()

            assert event.start < past
            assert event.end < past

            # recurring events may be in the past with one of
            # their occurrences in the future
            if not has_future_occurrences(event, past):
                past_events.append(event)

        past_events = [p.id for p in past_events]

        if past_events:
            log.info('removing past imported events -> %s' % str(past_events))

            if not dryrun:
                directory.manage_delObjects(past_events)
                pass
        else:
            log.info('no past imported events found')

        return past_events

    def cleanup_directory(self, directory, dryrun=True):

        if dryrun:
            log.info('starting dry run cleanup on %s' %
                     directory.absolute_url())
        else:
            log.info('starting real cleanup on %s' % directory.absolute_url())

        self.remove_stale_previews(directory, dryrun)
        self.archive_past_events(directory, dryrun)
        self.remove_archived_events(directory, dryrun)
        self.remove_past_imported_events(directory, dryrun)

        log.info('finished cleanup on %s' % directory.absolute_url())


cleanup_scheduler = CleanupScheduler()


class CleanupView(grok.View):

    grok.name('cleanup')
    grok.context(IEventsDirectory)
    grok.require('zope2.View')

    def render(self):
        self.request.response.setHeader("Content-type", "text/plain")

        # dryrun must be disabled explicitly using &run=1
        dryrun = not self.request.get('run') == '1'
        force_run = bool(self.request.get('force', False))

        # this maintenance feature may be run unrestricted as it does not
        # leak any information and it's behavior cannot be altered by the
        # user. This allows for easy use via cronjobs.
        with unrestricted.run_as('Manager'):
            self.request.set('_authenticator', createToken())
            cleanup_scheduler.run(self.context, dryrun, force_run)

        return u''
