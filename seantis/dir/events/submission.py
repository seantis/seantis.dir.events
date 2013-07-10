from datetime import datetime
from plone.app.event.dx.behaviors import IEventBasic
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from seantis.dir.events.interfaces import IEventSubmissionData
from seantis.dir.events import dates


ANNOTATION_KEY = 'seantis.dir.events.submission-data'


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
                print "can't inject, missing %s" % field
                return False

        return True

    def inject_sane_dates(self):
        """ Takes the IEventSubmissionDate data and makes nice IEventBasic
        data out of it.

        """

        print "injecting sane dates"

        basic = IEventBasic(self.context)
        single_day = self.data['submission_date_type'] == ['date']

        local_tz = dates.default_timezone()
        in_local_tz = lambda date: dates.as_timezone(date, local_tz)

        if single_day:
            date, start, end = (
                self.data['submission_date'],
                self.data['submission_start_time'],
                self.data['submission_end_time']
            )

            basic.start = in_local_tz(datetime.combine(date, start))
            basic.end = in_local_tz(datetime.combine(date, end))

            basic.whole_day = self.data['submission_whole_day']
