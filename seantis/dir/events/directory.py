from five import grok
from plone.namedfile.field import NamedImage
from Products.CMFPlone.PloneBatch import Batch

from seantis.dir.base import directory
from seantis.dir.base.const import ITEMSPERPAGE
from seantis.dir.base.interfaces import IDirectory
from seantis.dir.events import utils
from seantis.dir.events import _
from seantis.dir.events.recurrence import occurrences

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
        return dict(cat1=_(u'What'), cat2=_(u'Where'), cat3=_(u'When'))

    def used_categories(self):
        return ('cat1', 'cat2', 'cat3')

    def unused_categories(self):
        return ('cat4',)

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

    @property
    def batch(self):   
        min_date, max_date = utils.event_range()

        events = []
        for item in self.items:
            events.extend(occurrences(item, min_date, max_date))

        datefilter = self.get_filter_terms().get('cat3')
        if datefilter:
            key = utils.filter_function(self.context, self.request, datefilter)
        else:
            key = 'is_this_month'

        events = filter(utils.filter_key(key), events)

        events.sort(key=lambda o: str(o.start))

        start = int(self.request.get('b_start') or 0)
        return Batch(events, ITEMSPERPAGE, start, orphan=1)