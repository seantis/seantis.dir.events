from datetime import datetime
from plone.app.event.dx.behaviors import IEventBasic, IEventRecurrence
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from seantis.dir.events.interfaces import IEventSubmissionData
from seantis.dir.events import dates


ANNOTATION_KEY = 'seantis.dir.events.submission-data'


def get_event_dates_from_submission(data):

    local_tz = dates.default_timezone()
    in_local_tz = lambda date: dates.as_timezone(date, local_tz)

    if data['submission_date_type'] == ['date']:
        date, start, end, whole_day, recurrence = (
            data['submission_date'],
            data['submission_start_time'],
            data['submission_end_time'],
            data['submission_whole_day'],
            data['submission_recurrence']
        )

        start = in_local_tz(datetime.combine(date, start))
        end = in_local_tz(datetime.combine(date, end))

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

            if self.ready_for_injection():
                self.inject_sane_dates()
        else:
            self.__dict__[name] = value

    def ready_for_injection(self):
        for field in self.fields:
            if field not in self.data:
                return False
        return True

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
