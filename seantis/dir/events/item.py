from five import grok
from zope.schema import TextLine
from collective.dexteritytextindexer import searchable

from seantis.dir.base import item
from seantis.dir.base import core
from seantis.dir.base import utils
from seantis.dir.base.interfaces import IFieldMapExtender, IDirectoryItem

from seantis.dir.events.directory import IEventsDirectory
from seantis.dir.events import _
  
class IEventsDirectoryItem(IDirectoryItem):
    """Extends the seantis.dir.IDirectoryItem."""

    pass

class EventsDirectoryItem(item.DirectoryItem):
    pass

class EventsDirectoryItemViewlet(grok.Viewlet):
    grok.context(IEventsDirectoryItem)
    grok.name('seantis.dir.events.item.detail')
    grok.require('zope2.View')
    grok.viewletmanager(item.DirectoryItemViewletManager)

    template = grok.PageTemplateFile('templates/listitem.pt')

class View(core.View):
    """Default view of a seantis.dir.events item."""
    grok.context(IEventsDirectoryItem)
    grok.require('zope2.View')

    template = grok.PageTemplateFile('templates/item.pt')

class ExtendedDirectoryItemFieldMap(grok.Adapter):
    """Adapter extending the import/export fieldmap of seantis.dir.events.item."""
    grok.context(IEventsDirectory)
    grok.provides(IFieldMapExtender)

    def __init__(self, context):
        self.context = context

    def extend_import(self, itemmap):
        itemmap.typename = 'seantis.dir.events.item'
        itemmap.interface = IEventsDirectoryItem

        extended = []
        
        itemmap.add_fields(extended, len(itemmap))