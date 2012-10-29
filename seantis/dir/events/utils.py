from Products.CMFCore.utils import getToolByName

from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope import i18n

def get_current_language(request):
    """Returns the current language"""
    portal_state = getMultiAdapter((getSite(), request), name=u'plone_portal_state')
    return portal_state.language()

def translate(request, text):
    lang = get_current_language(request)
    return i18n.translate(text, target_language=lang)

def render_ical_response(request, context, calendar):
    name = '%s.ics' % context.getId()
    request.RESPONSE.setHeader('Content-Type', 'text/calendar')
    request.RESPONSE.setHeader('Content-Disposition',
        'attachment; filename="%s"' % name
    )
    request.RESPONSE.write(calendar.to_ical())

def workflow_tool():
    return getToolByName(getSite(), "portal_workflow")