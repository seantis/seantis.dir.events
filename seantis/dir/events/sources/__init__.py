import inspect

from five import grok
from plone.dexterity.utils import createContentInContainer

from seantis.dir.events.interfaces import IEventsDirectory


signature_method = 'fetch_events'


def available_sources():
    """ Search through the available modules of seantis.dir.events.sources
    and make available the ones which implement the signature_method.

    The result is a dictionary (name of source => function).

    """

    from seantis.dir.events import sources

    callables = {}

    for name, module in inspect.getmembers(sources, inspect.ismodule):
        functions = dict(inspect.getmembers(module, inspect.isfunction))

        if signature_method in functions:
            callables[name] = functions[signature_method]

    return callables


class FetchView(grok.View):

    grok.name('fetch')
    grok.context(IEventsDirectory)
    grok.require('cmf.ManagePortal')

    def fetch(self, function):
        events = [e for e in function(self.request)]

        for event in events:
            obj = createContentInContainer(
                self.context, 'seantis.dir.events.item', **event
            )
            obj.submit()
            obj.publish()

    def render(self):
        source = self.request.get('source')
        sources = available_sources()

        assert source in sources

        self.fetch(sources[source])
