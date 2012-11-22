import re, json

import logging
log = logging.getLogger('seantis.dir.events')

from five import grok

from zope.component.hooks import getSite
from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implements
from ZPublisher.BaseRequest import DefaultPublishTraverse
from zExceptions import NotFound

from plone.app.layout.viewlets.interfaces import IHtmlHeadLinks

from zope.cachedescriptors import property as cacheproperty

from seantis.dir.base.directory import DirectoryCatalogMixin
from seantis.dir.base.interfaces import IDirectoryRoot
from seantis.dir.base.session import set_last_search

from seantis.dir.events.interfaces import IEventsDirectory

key = 'seantis-events-pageid'
pattern = r'[~-]{1}([a-zA-Z]+)[-]?'

clear = object()

def custom_pageid(request, pageid=None):
    if pageid is clear:
        request._custom_pageid = None
    elif pageid:
        request._custom_pageid = pageid
    elif hasattr(request, '_custom_pageid'):
        return request._custom_pageid
    else:
        return None

def custom_properties(directory, request):
    pageid = custom_pageid(request)
    
    if not pageid:
        return None

    try:
        custom = json.loads('\n'.join(getattr(directory, pageid)))
    except:
        log.exception('pageid json for %s is mal-formed' % pageid)
        return None

    return custom

def custom_file(path):
    if not path:
        return None

    try:
        return getSite().unrestrictedTraverse(path)
    except NotFound:
        return None

def custom_directory(directory, request):

    custom = custom_properties(directory, request) or {}
    path = custom.get('directory')

    if not path:
        return directory

    obj = getSite().unrestrictedTraverse(path)
    if IEventsDirectory.providedBy(obj):
        return obj
    else:
        return directory

class CustomDirectory(object):

    @cacheproperty.cachedIn('_custom')
    def custom_directory(self):
        return custom_directory(self.context, self.request)
    
class CustomPageHook(object):
    """Intercepts traversal for IImageRepository, but only for 'tags'.
    Everything else is left untouched.
    """

    implements(IPublishTraverse)

    def publishTraverse(self, request, name):
        
        match = re.match(pattern, name)
        if match:
            request._match_request = True
            pageid = match.group(1)
            
            log.debug('setting pageid to %s' % pageid)
            custom_pageid(request, pageid)

            custom = custom_properties(self, request) or {}
            if 'searchtext' in custom:
                set_last_search(self, custom.get('searchtext'))

            return self

        if not hasattr(request, '_match_request') and name == 'view' and not request.get_header('referer'):
            custom_pageid(request, clear)

        return DefaultPublishTraverse(self, request).publishTraverse(request, name)

class CustomPageViewlet(grok.Viewlet, DirectoryCatalogMixin):
    grok.context(IDirectoryRoot)
    grok.name('seantis.dir.events.custom')
    grok.require('zope2.View')
    grok.viewletmanager(IHtmlHeadLinks)
    grok.order(99) # as far below as possible

    template = grok.PageTemplateFile('templates/custom.pt')

    @cacheproperty.cachedIn('_custom_properties')
    def custom_properties(self):
        return custom_properties(self.context, self.request) or {}

    def custom_css(self):
        f = custom_file(self.custom_properties.get('css', ''))
        return f and f.absolute_url() or ''

    def custom_script(self):
        f = custom_file(self.custom_properties.get('script', ''))
        return f and f.absolute_url() or ''