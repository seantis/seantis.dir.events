from datetime import datetime, timedelta
from seantis.dir.events import _

def overlaps(start, end, otherstart, otherend):

    if otherstart <= start and start <= otherend:
        return True

    if start <= otherstart and otherstart <= end:
        return True

    return False

def to_utc(date):

    date = (date - date.utcoffset())
    return datetime(date.year, date.month, date.day, date.hour, date.minute)

def datecategories(start, end):
    
    start = to_utc(start)
    end = to_utc(end)

    today = datetime.utcnow()

    if end < today:
        yield _(u'Already Over')
        raise StopIteration

    this_morning = datetime(today.year, today.month, today.day)
    this_night = this_morning + timedelta(days=1, microseconds=-1)

    if overlaps(start, end, this_morning, this_night):
        yield _(u'Today')

    if overlaps(start, end, this_morning+timedelta(days=1), this_night+timedelta(days=1)):
        yield _(u'Tomorrow')