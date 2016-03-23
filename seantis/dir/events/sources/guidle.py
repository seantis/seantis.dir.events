import string

from datetime import timedelta
from dateutil.parser import parse
from five import grok
from logging import getLogger
from lxml import objectify
from seantis.dir.events.interfaces import (
    IExternalEventCollector,
    IExternalEventSourceGuidle,
    IGuidleClassifier,
    NoImportDataException
)
from urllib2 import urlopen
from zope.component import queryAdapter

log = getLogger('seantis.dir.events')


class DefaultGuidleClassfier(object):

    def classify(self, classifications):
        categories = set()
        for classification in classifications.iterchildren():
            if classification.attrib.get('type', '') != "PRIMARY":
                continue

            categories = set([
                tag.attrib.get('subcategoryName')
                for tag in classification.iterchildren()
            ])

        return categories


class EventsSourceGuidle(grok.Adapter):
    grok.context(IExternalEventSourceGuidle)
    grok.provides(IExternalEventCollector)

    def generate_recurrence(self, date):
        try:
            weekdays = list(date.weekdays.iterchildren())
            return "RRULE:FREQ=WEEKLY;BYDAY=%s" % ','.join(
                [d.text.upper() for d in weekdays]
            )
        except AttributeError:
            return ""

    def limit_recurrence(self, recurrence, end):
        if not end or not recurrence:
            return recurrence
        else:
            return recurrence + ';UNTIL=%s' % end.strftime('%Y%m%dT%H%MZ')

    def get_dates(self, date):

        def child(name):
            try:
                return getattr(date, name).text
            except AttributeError:
                return None

        return (
            child('startDate'), child('endDate'),
            child('startTime'), child('endTime')
        )

    def events(self, offer):
        """ Generates one event for each date in the guidle input. """

        dates = [d for d in offer.schedules.iterchildren()]
        if not dates:
            log.error(
                'offer with id %s has no dates, skipping' % offer.attrib['id']
            )

            raise StopIteration

        for date in dates:

            start, end, start_time, end_time = self.get_dates(date)

            event = {}

            event['id'] = offer.attrib['id']
            event['recurrence'] = self.generate_recurrence(date)
            event['start'] = parse(start)

            # the end date of recurring events seems to be the date of the
            # last occurrence, which makes sense since guidle only seems
            # to support daily occurences by weekday
            if end and not event['recurrence']:
                event['end'] = parse(end)

                # Sometimes events last over several days, we replace this
                # with a daily occurence
                if event['start'] != event['end']:
                    event['recurrence'] = self.limit_recurrence(
                        "RRULE:FREQ=DAILY", event['end'] + timedelta(days=1)
                    )
                    event['end'] = event['start']
            else:
                # if a recurrence exists it needs to be limited by the end date
                if event['recurrence']:
                    until = parse(end) + timedelta(days=1)
                    event['recurrence'] = self.limit_recurrence(
                        event['recurrence'], until
                    )

                event['end'] = event['start']

            if not any((start_time, end_time)):
                event['whole_day'] = True
            else:
                event['whole_day'] = False

                # Some recurrent events start/end at 00:00
                if start_time == end_time and event['recurrence']:
                    event['whole_day'] = True
                    start_time = None
                    end_time = None

            if start_time:
                event['start'] = parse(start_time, default=event['start'])

            if end_time:
                event['end'] = parse(end_time, default=event['end'])

            # if the event ends before it starts it means that we have a range
            # like this: 20:00 - 00:30, so the event really ends the next day
            if event['end'] < event['start']:
                event['end'] += timedelta(days=1)

            yield event

    def copy(self, event, node, expression):
        lines = map(string.strip, expression.split('\n'))

        for line in lines:
            if not line:
                continue

            key, children = map(string.strip, line.split('<-'))

            for child in map(string.strip, children.split(',')):
                if not hasattr(node, child):
                    continue

                if key in event:
                    event[key] += '\n\n' + getattr(node, child).text
                else:
                    event[key] = getattr(node, child).text

    def fetch(self, xml=None):
        try:
            if xml is None:
                xml = urlopen(self.context.url, timeout=300).read()
            root = objectify.fromstring(xml)

            offers = root.xpath(
                '*//guidle:offer',
                namespaces={'guidle': 'http://www.guidle.com'}
            )
        except:
            raise NoImportDataException()

        classifier = queryAdapter(self, IGuidleClassifier)
        if not classifier:
            classifier = DefaultGuidleClassfier()

        for offer in offers:

            last_update_of_offer = parse(
                offer.lastUpdateDate.text
            ).replace(
                microsecond=0
            )

            assert last_update_of_offer, """"
                offers should all have an update timestamp
            """

            for e in self.events(offer):

                e['fetch_id'] = self.context.url
                e['last_update'] = last_update_of_offer

                # so far all guidle events seem to be in this region
                e['timezone'] = 'Europe/Zurich'
                e['source_id'] = offer.attrib['id']

                # basic information
                self.copy(e, offer.offerDetail, """
                    title               <- title
                    short_description   <- shortDescription
                    long_description    <- longDescription, openingHours
                    prices              <- priceInformation
                    event_url           <- externalLink
                    location_url        <- homepage
                    registration        <- ticketingUrl
                """)

                # address
                self.copy(e, offer.address, """
                    locality    <- company
                    street      <- street
                    zipcode     <- zip
                    town        <- city
                    latitude    <- latitude
                    longitude   <- longitude
                """)

                # contact
                self.copy(e, offer.contact, """
                    organizer       <- company
                    contact_name    <- name
                    contact_email   <- email
                    contact_phone   <- telephone_1
                """)

                # categories
                e['cat1'] = classifier.classify(offer.classifications)
                e['cat2'] = set((e['town'],))

                # image (download later)
                try:
                    for image in list(
                            offer.offerDetail.images.iterchildren())[:1]:
                        self.copy(e, image, "image <- url")
                except AttributeError:
                    pass

                # attachments (download later)
                try:
                    attachments = list(
                        offer.offerDetail.attachments.iterchildren()
                    )[:2]
                    for ix, attachment in enumerate(attachments):
                        self.copy(e, attachment,
                                  "attachment_%i <- url" % (ix + 1))
                except AttributeError:
                    pass

                yield e
