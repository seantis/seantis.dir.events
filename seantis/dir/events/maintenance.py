from datetime import datetime, timedelta

from logging import getLogger
log = getLogger('seantis.dir.events')

from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.events.interfaces import IEventsDirectoryItem
from seantis.dir.events.recurrence import has_future_occurrences

def cleanup_directory(directory):

    log.info('starting cleanup on %s' % directory.absolute_url())

    catalog = IDirectoryCatalog(directory)
    query = catalog.catalog

    log.info('searching for stale previews')

    past = datetime.utcnow() - timedelta(days=7)
    stale_previews = query(
        path={'query': directory.getPhysicalPath(), 'depth': 1},
        object_provides=IEventsDirectoryItem.__identifier__,
        review_state=('preview'),
        modified={'query': past, 'range': 'max'}
    )
    stale_previews = [p.id for p in stale_previews]

    if stale_previews:
        log.info('deleting stale previews -> %s' % str(stale_previews))
        # directory.manage_delObjects(stale_previews)
    else:
        log.info('no stale previews found')

    log.info('archiving past events')

    # events are in the past if they have been over for two days
    # (not one, to ensure that they are really over in all timezones)
    past = datetime.utcnow() - timedelta(days=2)
    published_events = query(
        path={'query': directory.getPhysicalPath(), 'depth': 1},
        object_provides=IEventsDirectoryItem.__identifier__,
        review_state=('published', ),
        end={'query': past, 'range': 'max'}
    )

    past_events = []
    
    for event in map(catalog.get_object, published_events):
        assert past < event.start

        # recurring events may be in the past with one of
        # their occurrences in the future
        if not has_future_occurrences(event):
            past_events.append(event.id)

    if past_events:
        log.info('archiving past events -> %s' % str(past_events))
    else:
        log.info('no past events found')

    log.info('removing archived events')

    past = datetime.utcnow() - timedelta(days=30)
    archived_events = query(
        path={'query': directory.getPhysicalPath(), 'depth': 1},
        object_provides=IEventsDirectoryItem.__identifier__,
        review_state=('archived', ),
        end={'query': past, 'range': 'max'}
    )
    archived_events = [e.id for e in archived_events]

    if archived_events:
        log.info('removing archived events -> %s' % str(archived_events))
    else:
        log.info('no archived events to remove')

    log.info('finished cleanup')