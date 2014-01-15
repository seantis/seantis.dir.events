import json

from dateutil.parser import parse
from five import grok
from urllib import urlopen

from seantis.dir.events.dates import default_now
from seantis.dir.events.interfaces import (
    IExternalEventCollector,
    IExternalEventSourceSeantisJson
)


class EventsSourceSeantisJson(grok.Adapter):
    grok.context(IExternalEventSourceSeantisJson)
    grok.provides(IExternalEventCollector)

    def fetch(self, json_string=None):

        if json_string is None:
            json_string = urlopen(self.context.url).read()
        events = json.loads(json_string)

        for event in events:

            e = {}
            e['fetch_id'] = self.context.url
            e['last_update'] = default_now()
            e['source_id'] = event['id']

            e['id'] = event.get('id')
            e['title'] = event.get('title')
            e['short_description'] = event.get('short_description')
            e['long_description'] = event.get('long_description')
            cat1, cat2 = event.get('cat1'), event.get('cat2')
            e['cat1'] = set(cat1) if cat1 is not None else set()
            e['cat2'] = set(cat2) if cat2 is not None else set()
            e['start'] = parse(event.get('start')).replace(tzinfo=None)
            e['end'] = parse(event.get('end')).replace(tzinfo=None)
            e['recurrence'] = event.get('recurrence')
            e['whole_day'] = event.get('whole_day')
            e['timezone'] = event.get('timezone')
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
            e['image'] = event.get('image')
            e['attachment_1'] = event.get('attachment_1')
            e['attachment_2'] = event.get('attachment_2')
            e['submitter'] = event.get('submitter')
            e['submitter_email'] = event.get('submitter_email')

            yield e
