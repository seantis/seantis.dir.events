from datetime import datetime, timedelta

from logging import getLogger
log = getLogger('seantis.dir.events')

from seantis.dir.base.interfaces import IDirectoryCatalog

from seantis.dir.events.dates import to_utc
from seantis.dir.events.interfaces import IEventsDirectoryItem
from seantis.dir.events.recurrence import has_future_occurrences


def remove_stale_previews(directory, dryrun=False):

    catalog = IDirectoryCatalog(directory)
    query = catalog.catalog.unrestrictedSearchResults

    log.info('searching for stale previews')

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


def archive_past_events(directory, dryrun=False):

    catalog = IDirectoryCatalog(directory)
    query = catalog.catalog

    log.info('archiving past events')

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


def remove_archived_events(directory, dryrun=False):

    catalog = IDirectoryCatalog(directory)
    query = catalog.catalog

    log.info('removing archived events')

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


def cleanup_directory(directory, dryrun=True):

    if dryrun:
        log.info('starting dry run cleanup on %s' % directory.absolute_url())
    else:
        log.info('starting real cleanup on %s' % directory.absolute_url())

    remove_stale_previews(directory, dryrun)
    archive_past_events(directory, dryrun)
    remove_archived_events(directory, dryrun)

    log.info('finished cleanup on %s' % directory.absolute_url())
