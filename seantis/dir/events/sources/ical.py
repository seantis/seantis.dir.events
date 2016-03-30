import icalendar
import pytz

from datetime import date, datetime, timedelta
from five import grok
from logging import getLogger
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


def as_timezone(value, timezone):
    if isinstance(value, datetime):
        if value.tzinfo:
            return timezone.normalize(value)

        return timezone.localize(value)

    return timezone.localize(datetime(value.year, value.month, value.day))


def as_utc(value):
    return as_timezone(value, pytz.UTC)


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

            uid = event.get('uid', '').encode('utf-8')
            start = event.get('dtstart', Missing()).dt
            end = event.get('dtend', Missing()).dt
            duration = event.get('duration', Missing()).dt

            e['whole_day'] = False
            if type(start) is date and type(end) is date:
                e['whole_day'] = True

            if type(start) is date:
                start = as_timezone(start, pytz.timezone('Europe/Zurich'))
            if type(end) is date:
                end = as_timezone(end, pytz.timezone('Europe/Zurich'))
                end = end - timedelta(microseconds=1)

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

            e['fetch_id'] = self.context.url
            e['last_update'] = event.get('last-modified', Missing()).dt
            e['source_id'] = uid
            e['title'] = event.get('summary', '').encode('utf-8')
            e['locality'] = event.get('location', '').encode('utf-8')
            des = event.get('description', '').encode('utf-8')
            des = self.context.default_description if not des else des
            e['short_description'] = des
            organizer = event.get('organizer', '').encode('utf-8')
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
