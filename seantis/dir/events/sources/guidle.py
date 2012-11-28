import pytz
import string

from logging import getLogger
log = getLogger('seantis.dir.events')

from datetime import datetime, timedelta
from dateutil.tz import tzoffset

from lxml import objectify
from urllib import urlopen


def create_uuid(offer):
    pass


def parse_offset(string):

    if not string:
        return 0

    sign = string[:1]
    assert sign in ('+', '-')

    tz = string.replace(sign, '')

    hours, minutes = map(int, tz.split(':'))
    seconds = hours * 60 * 60 + minutes * 60

    if sign == '+':
        return seconds
    else:
        return -seconds


def parse_date(string):
    date, tz = string[:10], string[10:]
    date = datetime.strptime(date, '%Y-%m-%d')
    date = date.replace(tzinfo=tzoffset(None, parse_offset(tz)))

    return date.astimezone(pytz.timezone('utc'))


def parse_time(string):
    time = string.replace(string[-6:], '')
    hour, minute = map(int, time.split(':')[:2])
    offset = parse_offset(string[-6:])

    return hour, minute, offset


def apply_time(datetime, timestring):
    assert datetime.tzinfo == pytz.timezone('utc')

    hour, minute, offset = parse_time(timestring)

    datetime = datetime.astimezone(tzoffset(None, offset))

    datetime += timedelta(seconds=hour * 60 * 60)
    datetime += timedelta(seconds=minute * 60)

    return datetime.astimezone(pytz.timezone('utc'))


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
        event['start'] = parse_date(start)

        # the end date of recurring events seems to be the date of the
        # last occurrence, which makes sense since guidle only seems
        # to support daily occurences by weekday
        if end and not event['recurrence']:
            event['end'] = parse_date(end)
        else:
            # if a recurrence exists it needs to be limited by the end date
            if event['recurrence']:
                until = parse_date(end) + timedelta(days=1)
                event['recurrence'] = limit_recurrence(
                    event['recurrence'], until
                )

            event['end'] = event['start']

        if not any((start_time, end_time)):
            event['whole_day'] = True

        if start_time:
            event['start'] = apply_time(event['start'], start_time)

        if end_time:
            event['end'] = apply_time(event['end'], end_time)

        # if the event ends before it starts it means that we have a range
        # like this: 20:00 - 00:30, so the event really ends the next day
        if event['end'] < event['start']:
            event['end'] += timedelta(days=1)

        yield event


def fetch_events(request):

    # TODO have an interface to define urls
    url = (
        "http://www.guidle.com/dpAccess.jsf"
        "?id=89625083&language=de&dateOption=NA&primaryTreeId=23400386"
        "&tagIds=23400386&sorting=ungrouped&locationTreeId=83786753"
        "&where=83786753&template=XML2"
    )

    xml = urlopen(url).read()
    root = objectify.fromstring(xml)

    offers = root.xpath('*//guidle:offer',
        namespaces={'guidle': 'http://www.guidle.com'}
    )

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

    for offer in offers:

        for e in events(offer):
            # so far all guidle events seem to be in this region
            e['timezone'] = 'Europe/Zurich'

            # basic information
            copy(e, offer.offerDetail, """
                title               <- title
                short_description   <- shortDescription
                long_description    <- longDescription, openingHours
                prices              <- priceInformation
                event_url           <- externalLink
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

            e['source_id'] = offer.attrib['id']

            yield e
