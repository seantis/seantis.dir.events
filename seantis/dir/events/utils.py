import functools
import json
import pytz
import string
import urllib

from collections import defaultdict
from collective.geo.geographer.interfaces import IGeoreferenced
from plone.namedfile import NamedFile
from Products.CMFCore.utils import getToolByName
from seantis.dir.base.interfaces import IDirectoryCatalog
from zope import i18n
from zope.component import getMultiAdapter, getAdapter
from zope.component.hooks import getSite


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


def render_json_response(request, items, compact):
    request.response.setHeader("Content-Type", "application/json")
    request.response.setHeader("Access-Control-Allow-Origin", "*")  # CORS

    utc = pytz.timezone('utc')
    duplicates = set()

    result = []
    for idx, item in enumerate(items):
        if compact:
            if item.id in duplicates:
                continue
            duplicates.add(item.id)

        event = {}

        start = item.start
        end = item.end

        if not start.tzinfo:
            start = utc.localize(start)
        if not end.tzinfo:
            end = utc.localize(end)

        updated = item.modification_date.asdatetime().replace(microsecond=0)
        event['last_update'] = updated.isoformat()
        event['id'] = item.id
        event['url'] = item.url()
        event['title'] = item.title
        event['short_description'] = item.short_description
        event['long_description'] = item.long_description
        event['cat1'] = item.cat1
        event['cat2'] = item.cat2
        event['start'] = utc.normalize(start).isoformat()
        event['end'] = utc.normalize(end).isoformat()
        event['recurrence'] = item.recurrence if compact else ''
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
        event['submitter'] = item.submitter
        event['submitter_email'] = item.submitter_email

        event['images'] = []
        if isinstance(item.image, NamedFile):
            image = {}
            image['name'] = item.image.filename
            image['url'] = item.absolute_url() + '/@@images/image'
            event['images'].append(image)

        event['attachements'] = []
        if isinstance(item.attachment_1, NamedFile):
            attachement = {}
            attachement['name'] = item.attachment_1.filename
            attachement['url'] = item.absolute_url()
            attachement['url'] += '/@@download/attachment_1'
            event['attachements'].append(attachement)
        if isinstance(item.attachment_2, NamedFile):
            attachement = {}
            attachement['name'] = item.attachment_2.filename
            attachement['url'] = item.absolute_url()
            attachement['url'] += '/@@download/attachment_2'
            event['attachements'].append(attachement)

        event['longitude'] = None
        event['latitude'] = None
        try:
            geo = IGeoreferenced(item)
            if geo.type == 'Point':
                event['longitude'] = geo.coordinates[0]
                event['latitude'] = geo.coordinates[1]
        except TypeError:
            pass

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


def terms_match(item, term):
    """ Returns if an item matches the given terms: At least one item of each
    given categories must be present. """

    item_categories = item.categories
    if callable(item.categories):
        item_categories = item.categories()

    categories = defaultdict(list)
    for category, label, value in item_categories:
        if isinstance(value, basestring):
            categories[category].extend((value.strip(), ))
        else:
            categories[category].extend(map(string.strip, value))

    for key, term_values in term.items():

        if not term_values or term_values == '!empty':
            continue

        if isinstance(term_values, basestring):
            term_values = (term_values, )

        if not set(categories[key]) & set(term_values):
            return False

    return True


def recurrence_url(directory, event):
    baseurl = directory.absolute_url()
    baseurl += '?range=this_and_next_year&search=true&searchtext=%s'
    searchtext = ''
    if event.title:
        searchtext += event.title.encode('utf-8') + ' '
    if event.short_description:
        searchtext += event.short_description.encode('utf-8')
    searchtext = searchtext.strip()
    return baseurl % urllib.quote(searchtext)
