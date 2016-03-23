import json

from dateutil.parser import parse
from five import grok
from urllib import quote_plus
from urllib2 import urlopen
from seantis.dir.events.dates import default_now, as_timezone
from seantis.dir.events.interfaces import (
    IExternalEventCollector,
    IExternalEventSourceSeantisJson,
    NoImportDataException
)


def fix_tzinfo(date):
    """ Fix timezone information for dates parsed with dateutil."""
    if date.tzinfo and date.tzname():
        timezone = date.tzname()
        date.replace(tzinfo=None)
        date = as_timezone(date, timezone)
    return date


class EventsSourceSeantisJson(grok.Adapter):
    grok.context(IExternalEventSourceSeantisJson)
    grok.provides(IExternalEventCollector)

    def build_url(self):

        url = self.context.url.strip() + '?'
        url += 'type=json&compact=true'
        if self.context.import_imported:
            url += '&imported=1'
        if self.context.do_filter and (self.context.cat1 or self.context.cat2):
            url += '&filter=true'
            if self.context.cat1:
                cat = quote_plus(
                    self.context.cat1.strip().encode('utf-8')
                )
                url += '&cat1=' + cat
            if self.context.cat2:
                cat = quote_plus(
                    self.context.cat2.strip().encode('utf-8')
                )
                url += '&cat2=' + cat
        return url

    def fetch(self, json_string=None):

        try:
            if json_string is None:
                url = self.build_url()
                json_string = urlopen(url, timeout=300).read()

            events = json.loads(json_string)
        except:
            raise NoImportDataException()

        for event in events:

            cat1, cat2 = event.get('cat1'), event.get('cat2')
            cat1 = set(cat1) if cat1 is not None else set()
            cat2 = set(cat2) if cat2 is not None else set()

            if self.context.do_filter:
                if self.context.cat1:
                    if self.context.cat1:
                        if self.context.cat1 not in cat1:
                            continue
                    else:
                        continue
                if self.context.cat2:
                    if self.context.cat2:
                        if self.context.cat2 not in cat2:
                            continue
                    else:
                        continue

            e = {}
            e['fetch_id'] = self.context.url
            updated = event.get('last_update')
            e['last_update'] = parse(updated) if updated else default_now()
            e['source_id'] = event['id']

            e['id'] = event.get('id')
            e['title'] = event.get('title')
            e['short_description'] = event.get('short_description')
            e['long_description'] = event.get('long_description')
            e['cat1'] = cat1
            e['cat2'] = cat2

            timezone = event.get('timezone')
            start = fix_tzinfo(parse(event.get('start')))
            end = fix_tzinfo(parse(event.get('end')))

            e['timezone'] = timezone
            e['start'] = as_timezone(start, timezone)
            e['end'] = as_timezone(end, timezone)
            e['recurrence'] = event.get('recurrence')
            e['whole_day'] = event.get('whole_day')

            e['locality'] = event.get('locality')
            e['street'] = event.get('street')
            e['housenumber'] = event.get('housenumber')
            e['zipcode'] = event.get('zipcode')
            e['town'] = event.get('town')
            e['location_url'] = event.get('location_url')
            lon, lat = event.get('longitude'), event.get('latitude')
            e['longitude'] = str(lon) if lon is not None else None
            e['latitude'] = str(lat) if lon is not None else None
            e['organizer'] = event.get('organizer')
            e['contact_name'] = event.get('contact_name')
            e['contact_email'] = event.get('contact_email')
            e['contact_phone'] = event.get('contact_phone')
            e['prices'] = event.get('prices')
            e['event_url'] = event.get('event_url')
            e['registration'] = event.get('registration')
            e['submitter'] = event.get('submitter')
            e['submitter_email'] = event.get('submitter_email')

            try:
                e['image'] = event['images'][0]['url']
                e['image_name'] = event['images'][0]['name']
            except (TypeError, KeyError, IndexError):
                e['image'] = None

            try:
                e['attachment_1'] = event['attachements'][0]['url']
                e['attachment_1_name'] = event['attachements'][0]['name']
            except (TypeError, KeyError, IndexError):
                e['attachment_1'] = None
            try:
                e['attachment_2'] = event['attachements'][1]['url']
                e['attachment_2_name'] = event['attachements'][1]['name']
            except (TypeError, KeyError, IndexError):
                e['attachment_2'] = None

            yield e
