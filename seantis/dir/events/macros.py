from five import grok
from zope.interface import Interface
from seantis.dir.base import core

class View(core.View):
    """A numer of macros for use with seantis.dir.events"""

    grok.context(Interface)
    grok.require('zope2.View')
    grok.name('seantis-dir-events-macros')

    template = grok.PageTemplateFile('templates/macros.pt')