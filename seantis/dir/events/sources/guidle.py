import string

from logging import getLogger
log = getLogger('seantis.dir.events')

from datetime import timedelta
from dateutil.parser import parse

from lxml import objectify
from urllib import urlopen

from zope.component import getMultiAdapter
from zope.interface import Interface, Attribute


class IGuidleConfig(Interface):
    """ Multi Adapter Interface for context/request.
    See vbeo.seantis.dir.events.guidle for an example.

    """

    url = Attribute("Guidle URL to download from")

    classification = Attribute(
        "Name of classification to use (guidle:classification name)"
    )

    tagmap = Attribute(
        "Dictionary mapping tags to categories (guidle:classification tags)"
    )

    def on_event(root, offer, event):
        """ Called before an event is yielded to the source. Root is the
        xml root, offer is the xml offer element and event is the dictionary
        that is returned to the source handler.

        Since an offer may be split in multiple events this method may be
        called multiple times for each offer. The difference will be the
        event's dates.

        This function may then alter the event.

        """


def generate_recurrence(date):
    try:
        weekdays = list(date.weekdays.iterchildren())
        return "RRULE:FREQ=WEEKLY;BYDAY=%s" % ','.join(
            [d.text.upper() for d in weekdays]
        )
    except AttributeError:
        return ""


def limit_recurrence(recurrence, end):
    if not end or not recurrence:
        return recurrence
    else:
        return recurrence + ';UNTIL=%s' % end.strftime('%Y%m%dT%H%MZ')


def get_dates(date):

    def child(name):
        try:
            return getattr(date, name).text
        except AttributeError:
            return None

    return (
        child('startDate'), child('endDate'),
        child('startTime'), child('endTime')
    )


def events(offer):
    """ Generates one event for each date in the guidle input. """

    dates = [d for d in offer.schedules.iterchildren()]
    if not dates:
        log.error(
            'offer with id %s has no dates, skipping' % offer.attrib['id']
        )

        raise StopIteration

    for date in dates:

        start, end, start_time, end_time = get_dates(date)

        event = {}

        event['id'] = offer.attrib['id']
        event['recurrence'] = generate_recurrence(date)
        event['start'] = parse(start)

        # the end date of recurring events seems to be the date of the
        # last occurrence, which makes sense since guidle only seems
        # to support daily occurences by weekday
        if end and not event['recurrence']:
            event['end'] = parse(end)
        else:
            # if a recurrence exists it needs to be limited by the end date
            if event['recurrence']:
                until = parse(end) + timedelta(days=1)
                event['recurrence'] = limit_recurrence(
                    event['recurrence'], until
                )

            event['end'] = event['start']

        if not any((start_time, end_time)):
            event['whole_day'] = True
        else:
            event['whole_day'] = False

        if start_time:
            event['start'] = parse(start_time, default=event['start'])

        if end_time:
            event['end'] = parse(end_time, default=event['end'])

        # if the event ends before it starts it means that we have a range
        # like this: 20:00 - 00:30, so the event really ends the next day
        if event['end'] < event['start']:
            event['end'] += timedelta(days=1)

        yield event


def categories_by_tags(classification, tagmap):
    categories = set()

    for tagname in (c.attrib['name'] for c in classification.iterchildren()):
        for key in tagmap:
            if tagname.startswith(key):
                categories.add(tagmap[key])

    return categories


def copy(event, node, expression):
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


def fetch_events(context, request):

    config = getMultiAdapter((context, request), IGuidleConfig)

    xml = urlopen(config.url).read()
    root = objectify.fromstring(xml)

    offers = root.xpath(
        '*//guidle:offer',
        namespaces={'guidle': 'http://www.guidle.com'}
    )

    for offer in offers:

        last_update_of_offer = parse(
            offer.lastUpdateDate.text
        ).replace(
            microsecond=0
        )

        assert last_update_of_offer, """"
            offers should all have an update timestamp
        """

        for e in events(offer):

            e['fetch_id'] = config.url
            e['last_update'] = last_update_of_offer

            # so far all guidle events seem to be in this region
            e['timezone'] = 'Europe/Zurich'
            e['source_id'] = offer.attrib['id']

            # basic information
            copy(e, offer.offerDetail, """
                title               <- title
                short_description   <- shortDescription
                long_description    <- longDescription, openingHours
                prices              <- priceInformation
                event_url           <- externalLink
                location_url        <- homepage
                registration        <- ticketingUrl
            """)

            # address
            copy(e, offer.address, """
                locality    <- company
                street      <- street
                zipcode     <- zip
                town        <- city
                latitude    <- latitude
                longitude   <- longitude
            """)

            # contact
            copy(e, offer.contact, """
                organizer       <- company
                contact_name    <- name
                contact_email   <- email
                contact_phone   <- telephone_1
            """)

            # categories
            for classification in offer.classifications.iterchildren():

                if classification.attrib['name'] != config.classification:
                    continue

                e['cat1'] = categories_by_tags(classification, config.tagmap)
                e['cat2'] = set((e['town'],))

            # image (download later)
            try:
                for image in list(offer.offerDetail.images.iterchildren())[:1]:
                    copy(e, image, "image <- url")
            except AttributeError:
                pass

            # attachments (download later)
            try:
                attachments = list(
                    offer.offerDetail.attachments.iterchildren()
                )[:2]
                for ix, attachment in enumerate(attachments):
                    copy(e, attachment, "attachment_%i <- url" % (ix + 1))
            except AttributeError:
                pass

            config.on_event(root, offer, e)

            yield e
