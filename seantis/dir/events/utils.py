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