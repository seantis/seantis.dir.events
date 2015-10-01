import pytz

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, FR

from plone.app.event.base import default_timezone
from seantis.dir.events import utils
from seantis.dir.events import _

default_daterange = 'this_and_next_year'


def eventrange():
    """ Returns the daterange (start, end) in which events may exist. """
    now = default_now()
    this_morning = datetime(now.year, now.month, now.day)

    # to work in all timezones the lowest timezone has to be considered
    # for the morning (the last place where day x is still occurring)
    # according to http://en.wikipedia.org/wiki/List_of_UTC_time_offsets this
    # is Baker / Howland Island with an UTC Offset of -12
    return (
        this_morning - timedelta(seconds=60 * 60 * 12),
        this_morning + timedelta(days=365 * 2)
    )


def overlaps(start, end, otherstart, otherend):
    """ Returns true if the two date ranges somehow overlap. """

    if otherstart <= start and start <= otherend:
        return True

    if start <= otherstart and otherstart <= end:
        return True

    return False


def default_now():
    """ Returns the current time using the default_timezone from
    plone.app.event. Said timezone is either set globally or per user.

    """
    utcnow = to_utc(datetime.utcnow())
    return pytz.timezone(default_timezone()).normalize(utcnow)


def to_utc(date):
    """ Converts date to utc, making it timezone aware if not already. """
    return as_timezone(date, 'utc')


def delete_timezone(date):
    """ Removes the timezone from a date. """
    assert date.tzinfo
    return date.replace(tzinfo=None)


def as_timezone(date, timezone):
    """ Converts date to the given timezone, making it timezone aware if not
    already. Use this instead of date.astimezone, since said function does
    not account for daylight savings time. """
    timezone = pytz.timezone(timezone)
    if not date.tzinfo:
        date = timezone.localize(date)

    return timezone.normalize(date)


def as_rfc5545_string(datetime):
    """ Converts a datetime into the RFC5545 Datetime Form #2 as defined in
    http://tools.ietf.org/html/rfc5545#section-3.3.5

    """
    return to_utc(datetime).strftime('%Y%m%dT%H%M%SZ')


def is_whole_day(start, end):
    return all((
        start.hour == 0,
        start.minute == 0,
        start.second == 0,
        end.hour == 23,
        end.minute == 59,
        end.second == 59
    ))


def days_between(start, end):
    return [(start + timedelta(days=d)) for d in xrange((end - start).days)]


def combine_daterange(date, start_time, end_time):
    """ Combines a date, a start_time and an end_time into a start-datetime,
    end-datetime range.

    """
    if end_time >= start_time:
        return (
            datetime.combine(date, start_time),
            datetime.combine(date, end_time)
        )
    else:
        return (
            datetime.combine(date, start_time),
            datetime.combine(date + timedelta(days=1), end_time)
        )


def split_days_count(start, end):
    """ Returns 0 if the given daterange must be kept together and a number
    of splits that need to be created if not.

    If the event ends between 0:00 and 08:59 the new date is not counted as
    a new day. An event that goes through the night is not a two-day event.

    """

    days = (end.date() - start.date()).days

    if days == 0:
        return 0

    if 0 <= end.hour and end.hour <= 8:
        days -= 1

    return days


def human_date(date, request):
    now = default_now()

    if now.date() == date.date():
        return _(u'Today')

    if now.date() + timedelta(days=1) == date.date():
        return _(u'Tomorrow')

    calendar = request.locale.dates.calendars['gregorian']
    weekday = calendar.getDayNames()[date.weekday()]

    if now.year == date.year:
        return weekday + ' ' + date.strftime('%d.%m')
    else:
        return weekday + ' ' + date.strftime('%d.%m.%Y')


def human_date_short(date, request):
    now = default_now()

    if now.date() == date.date():
        return _(u'Today')

    if now.date() + timedelta(days=1) == date.date():
        return _(u'Tomorrow')

    if now.year == date.year:
        return date.strftime('%d.%m')
    else:
        return date.strftime('%d.%m.%Y')


def human_daterange(start, end, request):

    if is_whole_day(start, end):
        if split_days_count(start, end) < 1:
            return utils.translate(request, _(u'Whole Day'))
        else:
            if default_now().year == start.year:
                return start.strftime('%d.%m. - ') \
                    + end.strftime('%d.%m. ') \
                    + utils.translate(request, _(u'Whole Day'))
            else:
                return start.strftime('%d.%m.%Y. - ') \
                    + end.strftime('%d.%m.%Y. ') \
                    + utils.translate(request, _(u'Whole Day'))

    if split_days_count(start, end) < 1:
        return start.strftime('%H:%M - ') + end.strftime('%H:%M')
    else:
        if default_now().year == start.year:
            return start.strftime('%d.%m. %H:%M - ') \
                + end.strftime('%d.%m. %H:%M')
        else:
            return start.strftime('%d.%m.%Y. %H:%M - ') \
                + end.strftime('%d.%m.%Y. %H:%M')

methods = list()
ranges = dict()
labels = dict()
tooltips = dict()


def daterange(label, tooltip=u''):
    """ Deocrator that, applied to DateRangeInfo methods, marks them
    as category methods for further processing.

    """
    tooltip = tooltip or label

    def decorator(fn):
        global methods, ranges, labels, tooltips

        methods.append((fn.__name__, label, tooltip))
        ranges[label] = fn.__name__
        labels[fn.__name__] = label
        tooltips[fn.__name__] = tooltip

        return fn

    return decorator


def is_valid_daterange(name):
    """ Returns true if the given name is a valid DateRangeInfo method. """
    return name in ranges.values()


weekdays = dict(MO=0, TU=1, WE=2, TH=3, FR=4, SA=5, SU=6)


def this_weekend(date):
    """ Returns a daterange with the start being friday 4pm and the end
    being sunday midnight, relative to the given date.

    """
    this_morning = datetime(
        date.year, date.month, date.day, 0, 0, tzinfo=date.tzinfo
    )

    if this_morning.weekday() in (weekdays["SA"], weekdays["SU"]):
        weekend_start = this_morning + relativedelta(weekday=FR(-1))
    else:
        weekend_start = this_morning + relativedelta(weekday=FR(+1))

    weekend_end = weekend_start + relativedelta(weekday=MO(1))

    weekend_start += timedelta(hours=16)
    weekend_end += timedelta(microseconds=-1)

    return weekend_start, weekend_end


def this_month(date):
    month_start = datetime(date.year, date.month, 1, 0, 0, tzinfo=date.tzinfo)
    month_end = month_start + relativedelta(months=1, microseconds=-1)

    return month_start, month_end


def next_weekday(date, weekday):
    w = weekdays[weekday]

    if date.weekday() == w:
        return date

    return date + timedelta((w - date.weekday()) % 7)


def as_range(start, end):
    start = datetime(start.year, start.month, start.day, tzinfo=start.tzinfo)
    end = datetime(end.year, end.month, end.day, tzinfo=end.tzinfo)
    end = end + timedelta(days=1, microseconds=-1)
    return start, end


class DateRanges(object):

    def __init__(self, now=None):
        self.now = now or default_now()

    def get_now(self):
        return self._now

    def set_now(self, now):
        self._now = now

        self.this_morning = datetime(
            now.year, now.month, now.day, tzinfo=now.tzinfo
        )
        self.this_evening = self.this_morning + timedelta(
            days=1, microseconds=-1
        )

        # mornings shall start at 3 am
        self.this_morning += timedelta(hours=3)

    now = property(get_now, set_now)

    def overlaps(self, method, start, end):
        s, e = getattr(self, method)
        return overlaps(s, e, start, end)

    @property
    @daterange(_(u'Today'))
    def today(self):
        return self.this_morning, self.this_evening

    @property
    @daterange(_(u'Tomorrow'))
    def tomorrow(self):
        return (
            self.this_morning + timedelta(days=1),
            self.this_evening + timedelta(days=1)
        )

    @property
    def day_after_tomorrow(self):
        return (
            self.this_morning + timedelta(days=2),
            self.this_evening + timedelta(days=2)
        )

    @property
    @daterange(
        _(u'This Weekend'), _(u'From 4pm this Friday until 12pm this Sunday')
    )
    def this_weekend(self):
        # between friday at 4 and saturday midnight
        return this_weekend(self.now)

    @property
    def next_weekend(self):
        weekend_start, weekend_end = this_weekend(self.now)
        weekend_start += timedelta(days=7)
        weekend_end += timedelta(days=7)

        return weekend_start, weekend_end

    @property
    @daterange(_(u'This Week'), _(u'From today until 12pm this Sunday'))
    def this_week(self):
        # range between now and next sunday evening with
        # range contains at least two days (saturday until next sunday)
        end_of_week = next_weekday(self.this_evening + timedelta(days=2), "SU")
        return self.this_morning, end_of_week

    @property
    def next_week(self):
        # range between next sunday (as in self.is_this_week)
        # and the sunday after that
        start_of_week = next_weekday(
            self.this_morning + timedelta(days=2), "SU"
        )
        start_of_week += timedelta(days=1)
        start_of_week = datetime(
            start_of_week.year, start_of_week.month, start_of_week.day, 0, 0,
            tzinfo=self.now.tzinfo
        )
        end_of_week = next_weekday(start_of_week, "SU") \
            + timedelta(days=1, microseconds=-1)

        return start_of_week, end_of_week

    @property
    @daterange(_(u'This Month'), _(u'From today until the end of the month'))
    def this_month(self):
        _, end_of_this_month = this_month(self.now)
        return self.this_morning, end_of_this_month

    @property
    def next_month(self):
        _, prev_end = this_month(self.now)
        month_start = prev_end + timedelta(microseconds=1)

        return this_month(month_start)

    @property
    @daterange(
        _(u'This Year'), _(u'From today until the end of this year')
    )
    def this_year(self):
        end_of_year = datetime(
            self.now.year + 1, 1, 1, tzinfo=self.now.tzinfo
        )
        end_of_year -= timedelta(microseconds=1)

        return self.this_morning, end_of_year

    @property
    def next_year(self):
        start_of_year = datetime(
            self.now.year + 1, 1, 1, tzinfo=self.now.tzinfo
        )
        end_of_year = datetime(self.now.year + 2, 1, 1, tzinfo=self.now.tzinfo)
        end_of_year -= timedelta(microseconds=1)

        return start_of_year, end_of_year

    @property
    @daterange(
        _(u'This and Next Year'), _(u'From today until the end of next year')
    )
    def this_and_next_year(self):
        return self.this_year[0], self.next_year[1]

    @property
    @daterange(_(u'From ... to ...'), _(u'Custom date range'))
    def custom(self):
        # These values are only used to as default values and are overwritten
        return self.this_month
