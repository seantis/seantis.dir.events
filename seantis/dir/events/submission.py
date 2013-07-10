from datetime import datetime, time
from plone.app.event.dx.behaviors import IEventBasic, IEventRecurrence
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from seantis.dir.events.interfaces import IEventSubmissionData
from seantis.dir.events import dates


ANNOTATION_KEY = 'seantis.dir.events.submission-data'


def get_event_dates_from_submission(data):

    local_tz = dates.default_timezone()
    in_local_tz = lambda date: dates.as_timezone(date, local_tz)

    single_day = data['submission_date_type'] == ['date']

    if single_day:
        date, start, end, whole_day, recurrence = (
            data['submission_date'],
            data['submission_start_time'],
            data['submission_end_time'],
            data['submission_whole_day'],
            data['submission_recurrence']
        )

        start, end = map(
            in_local_tz, dates.combine_daterange(date, start, end)
        )

        return start, end, whole_day, recurrence
    else:
        start_date, end_date, start_time, end_time, whole_day = (
            data['submission_range_start_date'],
            data['submission_range_end_date'],
            data['submission_range_start_time'],
            data['submission_range_end_time'],
            data['submission_whole_day']
        )

        if whole_day:
            start_time = time(0, 0, 0)
            end_time = time(23, 59, 59)

        start, end = map(
            in_local_tz, dates.combine_daterange(
                start_date, start_time, end_time
            )
        )

        recurrence = 'RRULE:FREQ=DAILY;UNTIL={}'.format(
            dates.as_rfc5545_string(
                in_local_tz(
                    datetime.combine(end_date, time(23, 59, 59))
                )
            )
        )

        return start, end, whole_day, recurrence


class EventSubmissionData(object):

    implements(IEventSubmissionData)

    def __init__(self, context):
        self.context = context
        self.fields = IEventSubmissionData.names()
        self.annotation = IAnnotations(self.context)
        self.data = self.annotation.get(ANNOTATION_KEY, {})
        self.annotation[ANNOTATION_KEY] = self.data

    def __getattr__(self, name):
        if name in self.__dict__.get('fields', []):
            if name in self.data:
                return self.data[name]

        raise AttributeError

    def __setattr__(self, name, value):
        if name in self.__dict__.get('fields', []):
            self.data[name] = value
        else:
            self.__dict__[name] = value

    def inject_sane_dates(self):
        """ Takes the IEventSubmissionDate data and makes nice IEventBasic
        data out of it.

        """
        basic = IEventBasic(self.context)
        recurring = IEventRecurrence(self.context)

        (
            basic.start,
            basic.end,
            basic.whole_day,
            recurring.recurrence
        ) = get_event_dates_from_submission(self.data)

        self.submission_recurrence = recurring.recurrence
