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

    def get_last_filter_method(self):
        return session.get_session(self.context, 'filter_method') or 'is_this_month'

    def set_last_filter_method(self, method):
        session.set_session(self.context, 'filter_method', method)

    def update(self, **kwargs):
        filter_method = self.request.get('range', self.get_last_filter_method())

        # do not trust the user's input blindly
        if not dates.is_valid_method(filter_method):
            filter_method = 'is_this_month'
        else:
            self.set_last_filter_method(filter_method)

        self.catalog.filter_method = filter_method

        super(EventsDirectoryView, self).update(**kwargs)

    @property
    def selected_filter_method(self):
        return self.catalog.filter_method

    def filter_methods(self):
        return dates.methods

    def filter_url(self, method):
        return self.directory.absolute_url() + '?range=' + method

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