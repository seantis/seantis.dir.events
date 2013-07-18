from datetime import datetime, time
from plone.app.event.dx.behaviors import IEventBasic, IEventRecurrence
from z3c.form.interfaces import ActionExecutionError
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements, Invalid
from seantis.dir.events.interfaces import IEventSubmissionData
from seantis.dir.events import dates
from seantis.dir.events import _
from seantis.dir.events.recurrence import occurrences_over_limit


ANNOTATION_KEY = 'seantis.dir.events.submission-data'


def validate_event_submission(data):

    def fail(msg):
        raise ActionExecutionError(Invalid(msg))

    if data['submission_date_type'] == ['date']:
        if data.get('submission_date') is None:
            fail(_(u'Missing start date'))

        if not data.get('submission_whole_day', False):
            if data.get('submission_start_time') is None:
                fail(_(u'Missing start time'))
            if data.get('submission_end_time') is None:
                fail(_(u'Missing end time'))

    if data['submission_date_type'] == ['range']:
        if data.get('submission_range_start_date') is None:
            fail(_(u'Missing start date'))
        if data.get('submission_range_end_date') is None:
            fail(_(u'Missing end date'))

        if not data.get('submission_whole_day', False):
            if data.get('submission_range_start_time') is None:
                fail(_(u'Missing start time'))
            if data.get('submission_range_end_time') is None:
                fail(_(u'Missing end time'))

    start, end, whole_day, recurrence = get_event_dates_from_submission(data)

    if not start:
        fail(_(u'Missing start date'))

    if not end:
        fail(_(u'Missing end date'))

    if end < start:
        fail(_(u'Start date after end date'))

    # ensure that the recurrences are not over limit
    if recurrence:

        limit = 365  # one event each day for a whole year

        if occurrences_over_limit(recurrence, start, limit):
            fail(
                _(
                    u'You may not add more than ${max} occurences',
                    mapping={'max': limit}
                )
            )


def get_event_dates_from_submission(data, timezone=None):

    timezone = timezone or dates.default_timezone()
    in_timezone = lambda date: dates.as_timezone(date, timezone)

    single_day = data['submission_date_type'] == ['date']

    if single_day:
        date, start, end, whole_day, recurrence = (
            data['submission_date'],
            data['submission_start_time'],
            data['submission_end_time'],
            data['submission_whole_day'],
            data['submission_recurrence']
        )

        if whole_day:
            start = time(0, 0, 0)
            end = time(23, 59, 59)

        start, end = map(
            in_timezone, dates.combine_daterange(date, start, end)
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
            in_timezone, dates.combine_daterange(
                start_date, start_time, end_time
            )
        )

        recurrence = 'RRULE:FREQ=WEEKLY;UNTIL={}'.format(
            dates.as_rfc5545_string(in_timezone(
                datetime.combine(end_date, time(23, 59, 59))
            ))
        )

        if data['submission_days']:
            recurrence += ';BYDAY={}'.format(
                ','.join(
                    [str(d) for d in data['submission_days']]
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
        ) = get_event_dates_from_submission(self.data, basic.timezone)

        self.submission_recurrence = recurring.recurrence
