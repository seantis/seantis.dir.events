import re, json

import logging
log = logging.getLogger('seantis.dir.events')

from five import grok

from zope.component.hooks import getSite
from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implements
from ZPublisher.BaseRequest import DefaultPublishTraverse

from plone.app.layout.viewlets.interfaces import IHtmlHeadLinks

from zope.cachedescriptors import property as cacheproperty

from seantis.dir.base.directory import DirectoryCatalogMixin
from seantis.dir.base.interfaces import IDirectoryRoot
from seantis.dir.base.session import get_session, set_session

key = 'seantis-events-pageid'
pattern = r'-([a-zA-Z]+)-'

def get_custom_pageid():
    return get_session(getSite(), key)

def set_custom_pageid(pageid):
    set_session(getSite(), key, pageid)

def clear_custom_pageid():
    set_session(getSite(), key, None)

def custom_properties(directory, pageid=None):
    pageid = pageid or get_custom_pageid()
    
    if not pageid:
        return None

    if not hasattr(directory, pageid):
        log.debug('pageid %s not found' % pageid)
        return None

    try:
        custom = json.loads('\n'.join(getattr(directory, pageid)))
    except:
        log.exception('pageid json for %s is mal-formed' % pageid)
        return None

    return custom

class CustomPageMixin(object):
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
            set_custom_pageid(pageid)

            return self

        if not hasattr(request, '_match_request') and name == 'view' and not request.get_header('referer'):
            clear_custom_pageid()

        return DefaultPublishTraverse(self, request).publishTraverse(request, name)

class CustomPageViewlet(grok.Viewlet, DirectoryCatalogMixin):
    grok.context(IDirectoryRoot)
    grok.name('seantis.dir.events.custom')
    grok.require('zope2.View')
    grok.viewletmanager(IHtmlHeadLinks)
    grok.order(99) # as far below as possible

    template = grok.PageTemplateFile('templates/custom.pt')

    @cacheproperty.cachedIn('_custom')
    def custom(self):
        return custom_properties(self.directory) or {}

    def custom_css(self):
        return self.custom.get('css', '')

    def custom_script(self):
        return self.custom.get('script', '')