import pytz

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, FR

from seantis.dir.events import _

def event_range():
    """ Returns the date range (start, end) in which the events are visible. """
    now = datetime.utcnow()
    this_morning = datetime(now.year, now.month, now.day)

    return (
        to_utc(this_morning),
        to_utc(datetime.utcnow() + timedelta(days=365*2))
    )

def overlaps(start, end, otherstart, otherend):
    """ Returns true if the two date ranges somehow overlap. """

    if otherstart <= start and start <= otherend:
        return True

    if start <= otherstart and otherstart <= end:
        return True

    return False

def to_utc(date):
    """ Converts date to utc, making it timezone aware if not already. """
    if not date.tzinfo:
        date = pytz.timezone('utc').localize(date)

    return pytz.timezone('utc').normalize(date)

def human_date(date, request, calendar_type='gregorian'):
    now = to_utc(datetime.utcnow())

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
        now = to_utc(datetime.utcnow())
        if now.year == start.year:
            return start.strftime('%d.%m %H:%M - ') + end.strftime('%d.%m %H:%M')
        else:
            return start.strftime('%d.%m.%Y %H:%M - ') + end.strftime('%d.%m.%Y %H:%M')

methods = list()
categories = dict()
labels = dict()

def category(label):
    """ Deocrator that, applied to DateRangeInfo methods, marks them
    as category methods for further processing. 

    """
    def decorator(fn):
        global methods, categories, labels

        methods.append((fn.__name__, label))
        categories[label] = fn.__name__
        labels[fn.__name__] = label
        
        return fn

    return decorator

def is_valid_method(name):
    """ Returns true if the given name is a valid DateRangeInfo method. """
    return name in categories.values()

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

class DateRangeInfo(object):

    __slots__ = ('_now', 's', 'e', 'this_morning', 'this_evening')

    def __init__(self, start, end):
        assert bool(start.tzinfo) == bool(end.tzinfo),\
        "Either both dates are timzone aware or naive, no mix"

        if start.tzinfo and end.tzinfo:
            self.now = to_utc(datetime.utcnow())
        else:
            self.now = datetime.utcnow()

        self.s, self.e = start, end

    @property
    def now(self):
        return self._now

    @now.setter
    def now(self, now):
        self._now = now
        self.this_morning = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
        self.this_evening = self.this_morning + timedelta(days=1, microseconds=-1)

    @property
    def is_over(self):
        return self.now > self.e

    @property
    @category(_(u'Today'))
    def is_today(self):
        return overlaps(self.s, self.e, self.this_morning, self.this_evening)

    @property
    @category(_(u'Tomorrow'))
    def is_tomorrow(self):
        return overlaps(self.s, self.e, 
            self.this_morning + timedelta(days=1),
            self.this_evening + timedelta(days=1)
        )

    @property
    @category(_(u'Day after Tomorrow'))
    def is_day_after_tomorrow(self):
        return overlaps(self.s, self.e,
            self.this_morning + timedelta(days=2),
            self.this_evening + timedelta(days=2),
        )

    @property
    @category(_(u'This Weekend'))
    def is_this_weekend(self):
        # between friday at 4 and saturday midnight

        weekend_start, weekend_end = this_weekend(self.now)
        return overlaps(self.s, self.e, weekend_start, weekend_end)

    @property
    @category(_(u'Next Weekend'))
    def is_next_weekend(self):
        weekend_start, weekend_end = this_weekend(self.now)
        weekend_start += timedelta(days=7)
        weekend_end += timedelta(days=7)

        return overlaps(self.s, self.e, weekend_start, weekend_end)

    @property
    @category(_(u'This Week'))
    def is_this_week(self):
        # range between now and next sunday evening with
        # range contains at least two days (saturday until next sunday)
        end_of_week = next_weekday(self.this_evening + timedelta(days=2), "SU")
        return overlaps(self.s, self.e, self.this_morning, end_of_week)

    @property
    @category(_(u'Next Week'))
    def is_next_week(self):
        # range between next sunday (as in self.is_this_week)
        # and the sunday after that
        start_of_week = next_weekday(self.this_morning + timedelta(days=2), "SU")
        start_of_week += timedelta(days=1)
        start_of_week = datetime(
            start_of_week.year, start_of_week.month, start_of_week.day, 0, 0,
            tzinfo=self.now.tzinfo
        )
        end_of_week = next_weekday(start_of_week, "SU") + timedelta(days=1, microseconds=-1)

        return overlaps(self.s, self.e, start_of_week, end_of_week)

    @property
    @category(_(u'This Month'))
    def is_this_month(self):
        month_start, month_end = this_month(self.now)

        return overlaps(self.s, self.e, month_start, month_end)

    @property
    @category(_(u'Next Month'))
    def is_next_month(self):
        prev_start, prev_end = this_month(self.now)
        month_start = prev_end + timedelta(microseconds=1)

        month_start, month_end = this_month(month_start)
        return overlaps(self.s, self.e, month_start, month_end)

    @property
    @category(_(u'This Year'))
    def is_this_year(self):
        return self.now.year in (self.s.year, self.e.year)

    @property
    @category(_(u'Next Year'))
    def is_next_year(self):
        return (self.now.year + 1) in (self.s.year, self.e.year)

def datecategories(start, end):
    """ Returns a list of datecategories for the given daterange. """
    
    daterange = DateRangeInfo(start, end)

    for method, name, unique in sorted(methods, key=lambda i: i[2], reverse=True):
        if getattr(daterange, method):
            yield name
            
            if unique:
                raise StopIteration

def filter_key(method):
    """ Returns a filter-key function that filters objects that have
    a start/end property according to the given method. 

    """
    def compare(item):
        return getattr(DateRangeInfo(item.start, item.end), method)

    return compare