import re, json

import logging
log = logging.getLogger('seantis.dir.events')

from five import grok

from zope.annotation.interfaces import IAnnotations
from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserRequest
from zExceptions import NotFound
from ZPublisher.BaseRequest import DefaultPublishTraverse

from plone.app.layout.viewlets.interfaces import IHtmlHeadLinks
from plone.transformchain.interfaces import ITransform

from zope.cachedescriptors import property as cacheproperty

from seantis.dir.base.directory import DirectoryCatalogMixin
from seantis.dir.base.interfaces import IDirectoryRoot, IDirectoryPage
from seantis.dir.base.session import set_last_search

from seantis.dir.events.interfaces import IEventsDirectory

key_pageid = 'seantis.dir.events.pageid'
key_url = 'seantis.dir.events.directory_url'

pattern = r'[~-]{1}([a-zA-Z]+)[-]?'

clear = object()

class CustomPageRequest(object):

    def __init__(self, request):
        self.request = request
        self.annotations = IAnnotations(request)

    def hook(self, pageid, directory):
        self.pageid = pageid
        self.url = directory.absolute_url()

        searchtext = self.properties(directory).get('searchtext')
        if searchtext:
            set_last_search(directory, searchtext)

    @property
    def pageid(self):
        return self.annotations.get(key_pageid)

    @pageid.setter
    def pageid(self, pageid):
        self.annotations[key_pageid] = pageid

    @property
    def url(self):
        return self.annotations.get(key_url)

    @url.setter
    def url(self, url):
        self.annotations[key_url] = url

    def properties(self, directory):
        if not self.pageid:
            return {}

        try:
            return json.loads('\n'.join(getattr(directory, self.pageid)))
        except:
            log.exception('pageid json for %s is mal-formed' % self.pageid)
            
            return {}

    def custom_directory(self, directory):
        props = self.properties(directory)
        path = props.get('directory')

        if not path:
            return directory

        obj = getSite().unrestrictedTraverse(path)
        if IEventsDirectory.providedBy(obj):
            return obj
        else:
            return directory

    def custom_file(self, directory, type):
        assert type in ('css', 'js')

        path = self.properties(directory).get(type)
        if not path:
            return None

        try:
            return getSite().unrestrictedTraverse(path)
        except NotFound:
            return None

class CustomDirectory(object):

    @cacheproperty.cachedIn('_custom')
    def custom_directory(self):
        pagerequest = CustomPageRequest(self.request)
        return pagerequest.custom_directory(self.context)
    
class CustomPageHook(object):
    """Intercepts traversal for IImageRepository, but only for 'tags'.
    Everything else is left untouched.
    """

    implements(IPublishTraverse)

    def publishTraverse(self, request, name):
        
        try:
            match = re.match(pattern, name)
            if match:
                request._match_request = True
                pageid = match.group(1)

                pagerequest = CustomPageRequest(request)
                pagerequest.hook(pageid, self)
                
                return self
        except Exception:
            # Zope will consume this exception and ignore it, so
            # we log it for the record
            log.exception('error while traversing')
            raise

        return DefaultPublishTraverse(self, request).publishTraverse(request, name)

class CustomPageViewlet(grok.Viewlet, DirectoryCatalogMixin):
    grok.context(IDirectoryRoot)
    grok.name('seantis.dir.events.custom')
    grok.require('zope2.View')
    grok.viewletmanager(IHtmlHeadLinks)
    grok.order(99) # as far below as possible

    template = grok.PageTemplateFile('templates/custom.pt')

    @cacheproperty.cachedIn('_custom_properties')
    def pagerequest(self):
        return CustomPageRequest(self.request)

    def custom_css(self):
        f = self.pagerequest.custom_file(self.context, 'css')
        return f and f.absolute_url() or ''

    def custom_script(self):
        f = self.pagerequest.custom_file(self.context, 'js')
        return f and f.absolute_url() or ''

from zope.interface import Interface
class URLTransform(object):
    implements(ITransform)
    adapts(IDirectoryPage, IBrowserRequest)

    order = 9001

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def transformString(self, result, encoding):
        return self.transformIterable([result], encoding)

    def transformUnicode(self, result, encoding):
        return self.transformIterable([result], encoding)

    def transformIterable(self, result, encoding):
        print "woah"
        pagerequest = CustomPageRequest(self.request)

        self.request.response.headers['x-page-id'] = pagerequest.pageid or ''
        self.request.response.headers['x-page-url'] = pagerequest.url or ''

        return result