from logging import getLogger
log = getLogger('seantis.dir.events')

import re
import threading

from five import grok

from ZServer.ClockServer import ClockServer

from seantis.dir.events.interfaces import IResourceViewedEvent


_clockservers = dict()  # list of registered Zope Clockservers
_lock = threading.Lock()


# The primary hook to setup maintenance clockservers is the reservation view
# event. It's invoked way too often, but the invocation is fast and it is
# guaranteed to be run on a plone site with seantis.events installed,
# setup and in use. Other events like zope startup and traversal events are
# not safe enough to use if one has to rely on a site being setup.
@grok.subscribe(IResourceViewedEvent)
def on_resource_viewed(event):
    path = '/'.join(event.context.getPhysicalPath())
    register(path + '/fetch?run=1', 15 * 60)
    register(path + '/cleanup?run=1', 60 * 60)


def clear_clockservers():
    """ Clears the clockservers and connections for testing. """

    with _lock:
        for cs in _clockservers.values():
            cs.close()
        _clockservers.clear()


def register(method, period):
    """ Registers the given method with a clockserver.

    Note that due to it's implementation there's no guarantee that the method
    will be called on time every time. The clockserver checks if a call is due
    every time a request comes in, or every 30 seconds when the asyncore.pollss
    method reaches it's timeout (see Lifetime/__init__.py and
    Python Stdlib/asyncore.py).

    """

    if method not in _clockservers:
        with _lock:
            _clockservers[method] = ClockServer(
                method, period, host='localhost', logger=ClockLogger(method)
            )

    return _clockservers[method]


logexpr = re.compile(r'GET [^\s]+ HTTP/[^\s]+ ([0-9]+)')


class ClockLogger(object):

    """ Logs the clock runs by evaluating the log strings. Looks for http
    return codes to do so.

    """

    def __init__(self, method):
        self.method = method

    def return_code(self, msg):
        groups = re.findall(logexpr, msg)
        return groups and int(groups[0]) or None

    def log(self, msg):
        code = self.return_code(msg)

        if not code:
            log.error("ClockServer for %s returned nothing" % self.method)
        elif code == 200:
            pass
        else:
            log.warn("ClockServer for %s returned %i" % (self.method, code))
