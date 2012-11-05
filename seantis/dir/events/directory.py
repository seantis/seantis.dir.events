from five import grok
from pytz import timezone

from datetime import datetime
from datetime import date as datetime_date
from urllib import urlopen
from icalendar import Calendar
from plone.dexterity.utils import createContent, addContentToContainer

from seantis.dir.base import directory
from seantis.dir.base import session

from seantis.dir.events.interfaces import IEventsDirectory
from seantis.dir.events.recurrence import grouped_occurrences
from seantis.dir.events import dates
from seantis.dir.events import utils
from seantis.dir.events import _

class EventsDirectory(directory.Directory):
    
    def labels(self):
        return dict(cat1=_(u'What'), cat2=_(u'Where'))

    def used_categories(self):
        return ('cat1', 'cat2')

    def unused_categories(self):
        return ('cat3', 'cat4')

class ExtendedDirectoryViewlet(grok.Viewlet):
    grok.context(IEventsDirectory)
    grok.name('seantis.dir.events.directory.detail')
    grok.require('zope2.View')
    grok.viewletmanager(directory.DirectoryViewletManager)

    template = grok.PageTemplateFile('templates/directorydetail.pt')

class EventsDirectoryView(directory.View):

    grok.name('view')
    grok.context(IEventsDirectory)
    grok.require('zope2.View')

    template = None
    _template = grok.PageTemplateFile('templates/directory.pt')

    @property
    def is_ical_export(self):
        """ Returns true if the current request is an ical request. """
        return self.request.get('type') == 'ical'

    def get_last_daterange(self):
        """ Returns the last selected daterange. """
        return session.get_session(self.context, 'daterange') or 'this_week'

    def set_last_daterange(self, method):
        """ Store the last selected daterange on the session. """
        session.set_session(self.context, 'daterange', method)

    @property
    def selected_daterange(self):
        return self.catalog.daterange

    @property
    def dateranges(self):
        return dates.methods

    def daterange_url(self, method):
        return self.directory.absolute_url() + '?range=' + method

    @property
    def has_results(self):
        return len(self.items) > 0

    def render(self):
        """ Renders the ical if asked, or the usual template. """
        if not self.is_ical_export:
            return self._template.render(self)
        else:
            if 'search' in self.request.keys():
                calendar = self.catalog.calendar(
                    search=self.request.get('searchtext')
                )
            elif 'filter' in self.request.keys():
                calendar = self.catalog.calendar(
                    filter=self.get_filter_terms()
                )
            else:
                calendar = self.catalog.calendar()

            utils.render_ical_response(self.request, self.context, calendar)

    def update(self, **kwargs):
        daterange = self.request.get('range', self.get_last_daterange())

        # do not trust the user's input blindly
        if not dates.is_valid_daterange(daterange):
            daterange = 'this_month'
        else:
            self.set_last_daterange(daterange)

        self.catalog.daterange = daterange

        if not self.is_ical_export:
            super(EventsDirectoryView, self).update(**kwargs)

    def groups(self, items):
        """ Returns the given occurrences grouped by human_date. """
        return grouped_occurrences(items, self.request)

    def ical_url(self, for_all):
        """ Returns the ical url of the current view. """
        url = self.daterange_url('this_year') + '&type=ical'
        
        if for_all:
            return url
        
        action, param = self.primary_action()

        if action not in (self.search, self.filter):
            return ''

        if action == self.search:
            if param:
                return url + '&search=true&searchtext=%s' % param
            else:
                return ''

        if action == self.filter:
            terms = dict([(k,v) for k, v in param.items() if v != '!empty'])
            
            if not terms:
                return ''

            url += '&filter=true'
            
            for item in terms.items():
                url += '&%s=%s' % item

            return url

class ImportIcsView(grok.View):

    grok.name('import-ics')
    grok.context(IEventsDirectory)
    grok.require('cmf.ManagePortal')

    messages = []

    @property
    def url(self):
        return self.request.get('url', '').replace('webcal://', 'https://')

    def say(self, text):
        self.messages.append(text)
        return '<br>'.join(self.messages)

    def read_ical(self):
        return urlopen(self.url).read()

    def valid_event(self, component):
        if component.name != 'VEVENT':
            return False

        required_fields = ('dtstart', 'dtend')

        for req in required_fields:
            if not req in component:
                return False

        return True

    def events(self, calendar):
        current_timezone = 'utc'
        for component in calendar.subcomponents:
            if component.name == 'VTIMEZONE':
                current_timezone = unicode(component['TZID'])

            if self.valid_event(component):
                component.timezone = current_timezone
                yield component

    def daterange(self, event):
        start = event['dtstart'].dt
        end = event['dtend'].dt

        if isinstance(start, datetime_date): 
            start = datetime(start.year, start.month, start.day, tzinfo=timezone(event.timezone))

        if isinstance(end, datetime_date):
            end = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone(event.timezone))

        return start, end

    def render(self):
        if not self.url:
            return self.say('No url given')

        calendar = Calendar.from_ical(self.read_ical())
        self.say('loaded %s' % self.url)

        events = list(self.events(calendar))
        self.say('found %i events' % len(events))

        for event in events:

            params = dict()
            params['title'] = unicode(event.get('summary', 'No Title'))
            params['short_description']= unicode(
                event.get('description', 'No Description')
            )

            params['start'], params['end'] = self.daterange(event)
            
            params['timezone'] = event.timezone
            params['whole_day'] = False
            params['recurrence'] = event.get('rrule', '')

            if params['recurrence']:
                params['recurrence'] = 'RRULE:' + params['recurrence'].to_ical()

            addContentToContainer(self.context, createContent(
                'seantis.dir.events.item', **params
            ))
            
        return self.say('events successfully imported')