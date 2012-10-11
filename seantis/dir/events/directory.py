from five import grok
from plone.namedfile.field import NamedImage
from itertools import groupby
from collections import OrderedDict

from seantis.dir.base import directory
from seantis.dir.base import session
from seantis.dir.base.interfaces import IDirectory
from seantis.dir.events import dates
from seantis.dir.events import _

class IEventsDirectory(IDirectory):
    """Extends the seantis.dir.base.directory.IDirectory"""

    image = NamedImage(
            title=_(u'Image'),
            required=False,
            default=None
        )

IEventsDirectory.setTaggedValue('seantis.dir.base.omitted', 
    ['cat1', 'cat2', 'cat3', 'cat4']
)

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
        return self.request.get('type') == 'ical'

    def get_last_daterange(self):
        return session.get_session(self.context, 'daterange') or 'this_month'

    def set_last_daterange(self, method):
        session.set_session(self.context, 'daterange', method)

    def render(self):
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


            name = '%s.ics' % self.context.getId()
            self.request.RESPONSE.setHeader('Content-Type', 'text/calendar')
            self.request.RESPONSE.setHeader('Content-Disposition',
                'attachment; filename="%s"' % name)
            self.request.RESPONSE.write(calendar.to_ical())

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

    @property
    def selected_daterange(self):
        return self.catalog.daterange

    def dateranges(self):
        return dates.methods

    def daterange_url(self, method):
        return self.directory.absolute_url() + '?range=' + method

    @property
    def has_results(self):
        return len(self.items) > 0

    def groups(self, items):
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
