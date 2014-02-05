import functools
import time
import json

from datetime import datetime

from Products.CMFCore.utils import getToolByName

from seantis.dir.base.interfaces import IDirectoryCatalog

from zope.component import getMultiAdapter, getAdapter
from zope.component.hooks import getSite
from zope import i18n

from plone.namedfile import NamedFile

from collective.geo.geographer.interfaces import IGeoreferenced


def get_catalog(directory):
    return getAdapter(directory, IDirectoryCatalog)


def get_current_language(request):
    """ Returns the current language """
    portal_state = getMultiAdapter(
        (getSite(), request), name=u'plone_portal_state'
    )
    return portal_state.language()


def translate(request, text, domain='seantis.dir.events'):
    lang = get_current_language(request)
    return i18n.translate(text, target_language=lang, domain=domain)


def render_ical_response(request, context, calendar):
    name = '%s.ics' % context.getId()
    request.RESPONSE.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
    request.RESPONSE.setHeader('Content-Disposition',
                               'attachment; filename="%s"' % name)
    return calendar.to_ical()


def render_json_response(request, items):
    request.response.setHeader("Content-Type", "application/json")
    request.response.setHeader("Access-Control-Allow-Origin", "*")  # CORS

    result = []
    for idx, item in enumerate(items):
        event = {}

        event['id'] = item.id
        event['title'] = item.title
        event['short_description'] = item.short_description
        event['long_description'] = item.long_description
        event['cat1'] = item.cat1
        event['cat2'] = item.cat2
        event['start'] = item.start.isoformat()
        event['end'] = item.end.isoformat()
        event['recurrence'] = item.recurrence
        event['whole_day'] = item.whole_day
        event['timezone'] = item.timezone
        event['locality'] = item.locality
        event['street'] = item.street
        event['housenumber'] = item.housenumber
        event['zipcode'] = item.zipcode
        event['town'] = item.town
        event['location_url'] = item.location_url
        event['organizer'] = item.organizer
        event['contact_name'] = item.contact_name
        event['contact_email'] = item.contact_email
        event['contact_phone'] = item.contact_phone
        event['prices'] = item.prices
        event['event_url'] = item.event_url
        event['registration'] = item.registration
        event['image'] = isinstance(item.image, NamedFile) \
            and 'image' or None
        event['attachment_1'] = isinstance(item.attachment_1, NamedFile) \
            and 'attachment_1' or None
        event['attachment_2'] = isinstance(item.attachment_2, NamedFile) \
            and 'attachment_2' or None
        event['submitter'] = item.submitter
        event['submitter_email'] = item.submitter_email

        try:
            geo = IGeoreferenced(item)
            event['coordinates'] = geo.coordinates
        except TypeError:
            event['coordinates'] = None

        result.append(event)

    return json.dumps(result)


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
