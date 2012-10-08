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

    template = grok.PageTemplateFile('templates/directory.pt')

    def get_last_daterange(self):
        return session.get_session(self.context, 'daterange') or 'this_month'

    def set_last_daterange(self, method):
        session.set_session(self.context, 'daterange', method)

    def update(self, **kwargs):
        daterange = self.request.get('range', self.get_last_daterange())

        # do not trust the user's input blindly
        if not dates.is_valid_daterange(daterange):
            daterange = 'this_month'
        else:
            self.set_last_daterange(daterange)

        self.catalog.daterange = daterange

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
            date = dates.human_date(item.start, self.request)
            return date

        groups = groupby(items, groupkey)
        
        # Zope Page Templates don't know how to handle generators :-|
        result = OrderedDict()

        for group in groups:
            result[group[0]] = [i for i in group[1]]
            
        return result

    def onclick(self, item):
        return 'window.location="%s";' % item.url()