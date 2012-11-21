import re, json

import logging
log = logging.getLogger('seantis.dir.events')

from zope.component.hooks import getSite
from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implements
from ZPublisher.BaseRequest import DefaultPublishTraverse

from seantis.dir.base.session import get_session, set_session

key = 'seantis-events-pageid'
pattern = r'-([a-zA-Z]+)-'

def get_custom_pageid():
    return get_session(getSite(), key)

def set_custom_pageid(pageid):
    set_session(getSite(), key, pageid)

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
            pageid = match.group(1)
            
            log.debug('setting pageid to %s' % pageid)
            set_custom_pageid(pageid)

            return self

        return DefaultPublishTraverse(self, request).publishTraverse(request, name)