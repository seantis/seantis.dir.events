import json
import pytz

from logging import getLogger
log = getLogger('seantis.dir.events')

from dateutil.parser import parse
from five import grok
from urllib import quote_plus
from urllib2 import urlopen

from seantis.dir.events.dates import default_now, as_timezone
from seantis.dir.events.interfaces import (
    IExternalEventCollector,
    IExternalEventSourceIcal,
    NoImportDataException
)

import icalendar


def fix_tzinfo(date):
    """ Fix timezone information for dates parsed with dateutil."""
    if date.tzinfo and date.tzname():
        timezone = date.tzname()
        date.replace(tzinfo=None)
        date = as_timezone(date, timezone)
    return date


class EventsSourceIcal(grok.Adapter):
    grok.context(IExternalEventSourceIcal)
    grok.provides(IExternalEventCollector)

    def fetch(self, ical=None):

        # try:
        #     if ical is None:
        #         ical = urlopen(self.context.url).read()
        #
        #     calendar = icalendar.Calendar.from_ical(ical)
        # except:
        #     raise NoImportDataException()

        # todo: no data etc

        if ical is None:
            ical = urlopen(self.context.url).read()

        calendar = icalendar.Calendar.from_ical(ical)

        # VERSION:2.0
        # PRODID:-//CodX Software AG//WinFAP TS 8.2
        # METHOD:PUBLISH
        # BEGIN:VTIMEZONE
        #     TZID:W. Europe Standard Time
        #     BEGIN:STANDARD
        #         DTSTART:16011028T030000
        #         TZOFFSETFROM:+0200
        #         TZOFFSETTO:+0100
        #         RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
        #     END:STANDARD
        #     BEGIN:DAYLIGHT
        #         DTSTART:16010325T020000
        #         TZOFFSETFROM:+0100
        #         TZOFFSETTO:+0200
        #         RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3
        #     END:DAYLIGHT
        # END:VTIMEZONE

        events = calendar.walk('vevent')
        for event in calendar.walk('vevent'):
            # BEGIN:VEVENT
            # UID:DD9F997D-CE47-4189-BCF5-54281E2E86AF
                # event.get('uid').title()
            # DTSTAMP:20150305T121424Z
                # event.get('dtstamp').dt

            # DTSTART;TZID="W. Europe Standard Time":20151029T193000
                # event.get('dtstart').dt
            # DURATION:PT2H0M0S
                # event.get('duration').dt

        #     cat1, cat2 = event.get('cat1'), event.get('cat2')
        #     cat1 = set(cat1) if cat1 is not None else set()
        #     cat2 = set(cat2) if cat2 is not None else set()
        #
        #     if self.context.do_filter:
        #         if self.context.cat1:
        #             if self.context.cat1:
        #                 if self.context.cat1 not in cat1:
        #                     continue
        #             else:
        #                 continue
        #         if self.context.cat2:
        #             if self.context.cat2:
        #                 if self.context.cat2 not in cat2:
        #                     continue
        #             else:
        #                 continue
        #
            e = {}
            import pdb; pdb.set_trace()

            # Zwingend
            # Titel
            # Kruzbeschrieb
            # Kategorien
            # Datum
            # Von/Bis oder Ganztags
            # Submitter Name und Submitter Email

            e['fetch_id'] = self.context.url

            last_update = event.get('last-modified')
            e['last_update'] = last_update.dt if last_update else default_now()

            # todo:
            source_id = event.get('uid')
            e['source_id'] = source_id.title() if source_id else '????'

        #     e['title'] = event.get('title')
            # SUMMARY;LANGUAGE=de:Kommandositzung
            #     event.get('summary').title()

        #     e['short_description'] = event.get('short_description')
        #     e['long_description'] = event.get('long_description')
        #     e['cat1'] = cat1
        #     e['cat2'] = cat2
        #
        #     timezone = event.get('timezone')
        #     start = fix_tzinfo(parse(event.get('start')))
        #     end = fix_tzinfo(parse(event.get('end')))
        #
        #     e['timezone'] = timezone
        #     e['start'] = as_timezone(start, timezone)
        #     e['end'] = as_timezone(end, timezone)
        #     e['recurrence'] = event.get('recurrence')
        #     e['whole_day'] = event.get('whole_day')
        #
        #     e['locality'] = event.get('locality')

                    # LOCATION;LANGUAGE=de:FW Depot 6312 Steinhausen
                        # event.get('location').title()


        #     e['street'] = event.get('street')
        #     e['housenumber'] = event.get('housenumber')
        #     e['zipcode'] = event.get('zipcode')
        #     e['town'] = event.get('town')
        #     e['location_url'] = event.get('location_url')
        #     lon, lat = event.get('longitude'), event.get('latitude')
        #     e['longitude'] = str(lon) if lon is not None else None
        #     e['latitude'] = str(lat) if lon is not None else None
        #     e['organizer'] = event.get('organizer')
        #     e['contact_name'] = event.get('contact_name')
        #     e['contact_email'] = event.get('contact_email')
        #     e['contact_phone'] = event.get('contact_phone')
        #     e['prices'] = event.get('prices')
        #     e['event_url'] = event.get('event_url')
        #     e['registration'] = event.get('registration')
        #     e['submitter'] = event.get('submitter')
        #     e['submitter_email'] = event.get('submitter_email')

                # ORGANIZER:DoNotReply@WinFAP.ch
                    # event.get('oraganizer').title()

        #
        #     try:
        #         e['image'] = event['images'][0]['url']
        #         e['image_name'] = event['images'][0]['name']
        #     except (TypeError, KeyError, IndexError):
        #         e['image'] = None
        #
        #     try:
        #         e['attachment_1'] = event['attachements'][0]['url']
        #         e['attachment_1_name'] = event['attachements'][0]['name']
        #     except (TypeError, KeyError, IndexError):
        #         e['attachment_1'] = None
        #     try:
        #         e['attachment_2'] = event['attachements'][1]['url']
        #         e['attachment_2_name'] = event['attachements'][1]['name']
        #     except (TypeError, KeyError, IndexError):
        #         e['attachment_2'] = None
        #
        #     yield e
