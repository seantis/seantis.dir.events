import icalendar

from datetime import datetime
from five import grok
from logging import getLogger
from pytz import UTC
from urllib2 import urlopen
from seantis.dir.events.interfaces import (
    IExternalEventCollector,
    IExternalEventSourceIcal,
    NoImportDataException
)

log = getLogger('seantis.dir.events')


class Missing():

    @property
    def dt(self):
        return None


def as_utc(value):
    if isinstance(value, datetime):
        if value.tzinfo:
            return UTC.normalize(value)

        return UTC.localize(value)

    return UTC.localize(datetime(value.year, value.month, value.day))


class EventsSourceIcal(grok.Adapter):
    grok.context(IExternalEventSourceIcal)
    grok.provides(IExternalEventCollector)

    def fetch(self, ical=None):
        try:
            if ical is None:
                ical = urlopen(self.context.url).read()

            calendar = icalendar.Calendar.from_ical(ical)
        except:
            raise NoImportDataException()

        for event in calendar.walk('vevent'):

            e = {}

            uid = str(event.get('uid', ''))
            start = event.get('dtstart', Missing()).dt
            end = event.get('dtend', Missing()).dt
            duration = event.get('duration', Missing()).dt

            if start and end:
                e['start'] = as_utc(start)
                e['end'] = as_utc(end)
            elif start and duration:
                e['start'] = as_utc(start)
                e['end'] = e['start'] + duration
            else:
                log.error('skipping event {} wtih invalid dates'.format(uid))
                continue

            # Unfortunately, we cannot use the timezone given in the ICS, these
            # might have unusable names such as "W. Europe Standard Time"
            # instead of olson names. We do the same here as with guidle and
            # assume Europe/Zurich!
            e['timezone'] = 'Europe/Zurich'
            e['whole_day'] = e['start'] == e['end']

            e['fetch_id'] = self.context.url
            e['last_update'] = event.get('last-modified', Missing()).dt
            e['source_id'] = uid
            e['title'] = str(event.get('summary', ''))
            e['locality'] = str(event.get('location', ''))
            des = str(event.get('description', ''))
            des = self.context.default_description if not des else des
            e['short_description'] = des
            organizer = str(event.get('organizer', ''))
            organizer = 'ical@example.com' if not organizer else organizer
            e['submitter'] = organizer
            e['submitter_email'] = organizer

            e['recurrence'] = ''
            e['long_description'] = ''
            e['cat1'] = set()
            e['cat2'] = set()
            e['street'] = ''
            e['housenumber'] = ''
            e['zipcode'] = ''
            e['town'] = ''
            e['location_url'] = ''
            e['longitude'] = None
            e['latitude'] = None
            e['organizer'] = ''
            e['contact_name'] = ''
            e['contact_email'] = ''
            e['contact_phone'] = ''
            e['prices'] = ''
            e['event_url'] = ''
            e['registration'] = ''
            e['image'] = None
            e['attachment_1'] = None
            e['attachment_2'] = None

            yield e
