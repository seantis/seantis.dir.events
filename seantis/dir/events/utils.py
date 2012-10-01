import pytz

from calendar import monthrange
from datetime import datetime, timedelta

from seantis.dir.events import _
from seantis.dir.base.utils import translate

def event_range():
    return (
        to_utc(datetime.utcnow() - timedelta(days=7)),
        to_utc(datetime.utcnow() + timedelta(days=365*2))
    )

def overlaps(start, end, otherstart, otherend):

    if otherstart <= start and start <= otherend:
        return True

    if start <= otherstart and otherstart <= end:
        return True

    return False

def to_utc(date):
    if not date.tzinfo:
        date = pytz.timezone('utc').localize(date)

    return pytz.timezone('utc').normalize(date)

weekdays = dict(MO=0, TU=1, WE=2, TH=3, FR=4, SA=5, SU=6)
def next_weekday(date, weekday):
    w = weekdays[weekday]

    if date.weekday() == w:
        return date
    
    return date + timedelta((w - date.weekday()) % 7)

def this_weekend(date):
    this_morning = datetime(date.year, date.month, date.day, 0, 0, tzinfo=date.tzinfo)

    if this_morning.weekday() == weekdays["SA"]:
        weekend_start = this_morning + timedelta(days=-1, hours=16)
    elif this_morning.weekday() == weekdays["SU"]:
        weekend_start = this_morning + timedelta(days=-2, hours=16)
    else:
        weekend_start = next_weekday(this_morning, "FR") + timedelta(hours=16)

    weekend_end = next_weekday(weekend_start, "SU")
    weekend_end += timedelta(hours=-16, days=1, microseconds=-1)

    return weekend_start, weekend_end

def this_month(date):
    last_day = monthrange(date.year, date.month)[1]
    month_start = datetime(date.year, date.month, 1, 0, 0, tzinfo=date.tzinfo)
    month_end = datetime(date.year, date.month, last_day, 0, 0, tzinfo=date.tzinfo)
    month_end += timedelta(days=1, microseconds=-1)

    return month_start, month_end

methods = list()
categories = dict()

def category(name, unique=False):
    def decorator(fn):
        global methods, categories

        methods.append((fn.__name__, name, unique))
        categories[name] = fn.__name__
        return fn

    return decorator

class DateRangeInfo(object):

    def __init__(self, start, end):
        if all((start.tzinfo, end.tzinfo)):
            self.now = to_utc(datetime.utcnow())
        elif not any((start.tzinfo, end.tzinfo)):
            self.now = datetime.utcnow()
        else:
            assert False, "Either both dates are timzone aware or naive, no mix"

        self.s = start
        self.e = end

    def get_now(self):
        return self._now

    def set_now(self, now):
        self._now = now
        self.this_morning = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
        self.this_evening = self.this_morning + timedelta(days=1, microseconds=-1)

    now = property(get_now, set_now)

    @property
    @category(_(u'Already Over'), unique=True)
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
    
    daterange = DateRangeInfo(start, end)

    for method, name, unique in sorted(methods, key=lambda i: i[2], reverse=True):
        if getattr(daterange, method):
            yield name
            
            if unique:
                raise StopIteration

def filter_function(context, request, text):

    localized = lambda text: translate(context, request, text)

    for key in categories:
        if text == localized(key):
            return categories[key]

    return None

def filter_key(filter_function_key):
    def compare(item):
        daterange = DateRangeInfo(item.start, item.end)
        return getattr(daterange, filter_function_key)

    return compare