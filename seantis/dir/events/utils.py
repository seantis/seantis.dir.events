import functools
import time

from Products.CMFCore.utils import getToolByName

from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope import i18n

def get_current_language(request):
    """ Returns the current language """
    portal_state = getMultiAdapter((getSite(), request), name=u'plone_portal_state')
    return portal_state.language()

def translate(request, text):
    lang = get_current_language(request)
    return i18n.translate(text, target_language=lang, domain='seantis.dir.events')

def render_ical_response(request, context, calendar):
    name = '%s.ics' % context.getId()
    request.RESPONSE.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
    request.RESPONSE.setHeader('Content-Disposition',
        'attachment; filename="%s"' % name
    )
    request.RESPONSE.write(calendar.to_ical())

def workflow_tool():
    return getToolByName(getSite(), "portal_workflow")

def verify_wkt(data):
    try:
        from shapely import wkt
        geom = wkt.loads(data)
    except ImportError:
        from pygeoif.geometry import from_wkt
        geom = from_wkt(data)
    return geom

def profile(fn):
    """ Naive profiling of a function.. on unix systems only. """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()

        result = fn(*args, **kwargs)
        print fn.__name__, 'took', (time.time() - start) * 1000, 'ms'

        return result

    return wrapper

def webcal(fn):
    """ Replaces the http in a function that returns an url with webcal.
    Does nothing if https is used, as webcals seems to be supported badly.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        url = fn(*args, **kwargs)
        
        if not url.startswith('https') and url.startswith('http'):
            url = url.replace('http', 'webcal')
        
        return url

    return wrapper