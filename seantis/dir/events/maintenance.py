from five import grok

from seantis.plonetools import async
from seantis.dir.events.interfaces import IResourceViewedEvent


# The primary hook to setup maintenance clockservers is the reservation view
# event. It's invoked way too often, but the invocation is fast and it is
# guaranteed to be run on a plone site with seantis.events installed,
# setup and in use. Other events like zope startup and traversal events are
# not safe enough to use if one has to rely on a site being setup.
@grok.subscribe(IResourceViewedEvent)
def on_resource_viewed(event):
    path = '/'.join(event.context.getPhysicalPath())
    async.register(path + '/fetch?run=1', 15 * 60)
    async.register(path + '/cleanup?run=1', 60 * 60)
