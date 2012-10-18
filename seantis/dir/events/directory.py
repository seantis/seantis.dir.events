from five import grok
from itertools import groupby
from collections import OrderedDict

from seantis.dir.base import directory
from seantis.dir.base import session

from seantis.dir.events.interfaces import IEventsDirectory
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
        return session.get_session(self.context, 'daterange') or 'this_month'

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
        """ Returns the given items grouped by human_date. """
        def groupkey(item):
            date = item.human_date(self.request)
            return date

        groups = groupby(items, groupkey)
        
        # Zope Page Templates don't know how to handle generators :-|
        result = OrderedDict()

        for group in groups:
            result[group[0]] = [i for i in group[1]]
            
        return result

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
