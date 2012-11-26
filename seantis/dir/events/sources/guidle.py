import pytz

from datetime import datetime, timedelta
from dateutil.tz import tzoffset

from lxml import objectify
from urllib import urlopen


def create_uuid(offer):
    pass


def parse_offset(string):

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
    hour, minute = map(int, string.split(':')[:2])
    offset = parse_offset(string[12:])

    return hour, minute, offset


def apply_time(datetime, timestring):
    hour, minute, offset = parse_time(timestring)
    datetime.replace(hour=hour, minute=minute)
    datetime += timedelta(seconds=offset)


def generate_recurrence(date):
    try:
        return "WEEKLY;BYDAY=%s" ','.join([d.upper() for d in date.weekdays])
    except AttributeError:
        return ""


def occurrences(offer, create_event):

    for schedule in offer.schedules:

        date = schedule.date

        start, end = date.startDate, date.endDate
        start_time, end_time = date.startTime, date.endTime

        event = create_event()

        event.timezone = 'UTC'
        event.recurrence = generate_recurrence(offer.date)
        event.start = parse_date(date.startDate)

        if end:
            event.end = parse_date(date.endDate)
        else:
            event.end = event.start + timedelta(days=1, microseconds=-1)

        if not any((start_time, end_time)):
            event.whole_day = True

        if start_time:
            apply_time(event.start, start_time)

        if end_time:
            apply_time(event.end, end_time)

        yield event


def generate_events(url, request, create_event):

    xml = urlopen(url)
    root = objectify.fromstring(xml)

    offers = root.xpath('*//guidle:offer',
        namespaces={'guidle': 'http://www.guidle.com'}
    )

    for offer in offers:
        for e in occurrences(offer, create_event):

            detail = offer.offerDetail

            e.title = detail.title
            e.short_description = detail.shortDescription
            e.long_description = detail.longDescription
