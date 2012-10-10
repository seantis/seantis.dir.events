import pytz

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, FR

from plone.app.event.base import default_timezone
from seantis.dir.events import _

def eventrange():
    """ Returns the date range (start, end) in which the events are visible. """
    now = default_now()
    this_morning = datetime(now.year, now.month, now.day)

    return (
        this_morning,
        this_morning + timedelta(days=365*2)
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
    if not date.tzinfo:
        date = pytz.timezone('utc').localize(date)

    return pytz.timezone('utc').normalize(date)

def human_date(date, request, calendar_type='gregorian'):
    now = default_now()

    if now.date() == date.date():
        return _(u'Today')

    if now.date() == (date.date() + timedelta(days=1)):
        return _(u'Tomorrow')

    calendar = request.locale.dates.calendars[calendar_type]
    weekday = calendar.getDayNames()[date.weekday()]

    if now.year == date.year:
        return weekday + ' ' + date.strftime('%d.%m')
    else:
        return weekday + ' ' + date.strftime('%d.%m.%Y')

def human_daterange(start, end):
    if (end - start).days < 1:
        return start.strftime('%H:%M - ') + end.strftime('%H:%M')
    else:
        now = default_now()
        if now.year == start.year:
            return start.strftime('%d.%m %H:%M - ') + end.strftime('%d.%m %H:%M')
        else:
            return start.strftime('%d.%m.%Y %H:%M - ') + end.strftime('%d.%m.%Y %H:%M')

methods = list()
ranges = dict()
labels = dict()

def daterange(label):
    """ Deocrator that, applied to DateRangeInfo methods, marks them
    as category methods for further processing. 

    """
    def decorator(fn):
        global methods, ranges, labels

        methods.append((fn.__name__, label))
        ranges[label] = fn.__name__
        labels[fn.__name__] = label

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
    this_morning = datetime(date.year, date.month, date.day, 0, 0, tzinfo=date.tzinfo)

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


class DateRanges(object):

    def __init__(self, now=None):
        self.now = now or default_now()

    @property
    def now(self):
        return self._now

    @now.setter
    def now(self, now):
        self._now = now
        self.this_morning = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
        self.this_evening = self.this_morning + timedelta(days=1, microseconds=-1)

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
        return (self.this_morning + timedelta(days=1),
                self.this_evening + timedelta(days=1)
        )

    @property
    @daterange(_(u'Day after Tomorrow'))
    def day_after_tomorrow(self):
        return (self.this_morning + timedelta(days=2),
                self.this_evening + timedelta(days=2)
        )

    @property
    @daterange(_(u'This Weekend'))
    def this_weekend(self):
        # between friday at 4 and saturday midnight
        return this_weekend(self.now)
        
    @property
    @daterange(_(u'Next Weekend'))
    def next_weekend(self):
        weekend_start, weekend_end = this_weekend(self.now)
        weekend_start += timedelta(days=7)
        weekend_end += timedelta(days=7)

        return weekend_start, weekend_end

    @property
    @daterange(_(u'This Week'))
    def this_week(self):
        # range between now and next sunday evening with
        # range contains at least two days (saturday until next sunday)
        end_of_week = next_weekday(self.this_evening + timedelta(days=2), "SU")
        return self.this_morning, end_of_week

    @property
    @daterange(_(u'Next Week'))
    def next_week(self):
        # range between next sunday (as in self.is_this_week)
        # and the sunday after that
        start_of_week = next_weekday(self.this_morning + timedelta(days=2), "SU")
        start_of_week += timedelta(days=1)
        start_of_week = datetime(
            start_of_week.year, start_of_week.month, start_of_week.day, 0, 0,
            tzinfo=self.now.tzinfo
        )
        end_of_week = next_weekday(start_of_week, "SU") + timedelta(days=1, microseconds=-1)

        return start_of_week, end_of_week

    @property
    @daterange(_(u'This Month'))
    def this_month(self):
        return this_month(self.now)

    @property
    @daterange(_(u'Next Month'))
    def next_month(self):
        prev_start, prev_end = this_month(self.now)
        month_start = prev_end + timedelta(microseconds=1)

        return this_month(month_start)

    @property
    @daterange(_(u'This Year'))
    def this_year(self):
        start_of_year = datetime(self.now.year, 1, 1, tzinfo=self.now.tzinfo)
        end_of_year = datetime(self.now.year+1, 1, 1, tzinfo=self.now.tzinfo)
        end_of_year -= timedelta(microseconds=1)

        return start_of_year, end_of_year

    @property
    @daterange(_(u'Next Year'))
    def next_year(self):
        start_of_year = datetime(self.now.year+1, 1, 1, tzinfo=self.now.tzinfo)
        end_of_year = datetime(self.now.year+2, 1, 1, tzinfo=self.now.tzinfo)
        end_of_year -= timedelta(microseconds=1)

        return start_of_year, end_of_year