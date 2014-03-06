""" Oh boy.

Event Calendars of small municiaplities have a somewhat higher chance of
being empty. So those towns end up sharing their events with other, bigger
towns in the area, increasing their chances of having a reasonably
full calendar.

This is a perfectly fine approach, but it has one drawback. There's only
one calendar with one corporate design. The 'CD'? Not a holy cow that
a mere mortal may slaughter.

To enable this, the idea was to give small towns the ability to use a
custom url to which they can link on their sites. Someone entering
the event calendar through that url would then be guaranteed to see
an alternative design throughout his stay.

So we ended up implementing what awaits below. We allow customers to
use special urls on event directories. We interpret those urls, get
custom properties from the directory and rewrite all the urls and
redirects having to do with said directory.

For the future we very much want to implement a different system to avoid
empty calendars, maybe using P2P calendar syncing. But that will take
a lot of work, so for now that's that.

"""

import re
import json

import logging
log = logging.getLogger('seantis.dir.events')

from urlparse import urlparse, urlunparse
from urllib import quote
from five import grok

from zope.annotation.interfaces import IAnnotations
from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserRequest
from zExceptions import NotFound
from ZPublisher.BaseRequest import DefaultPublishTraverse
from ZPublisher.interfaces import IPubSuccess

from plone.app.layout.viewlets.interfaces import IHtmlHeadLinks
from plone.app.theming.transform import ThemeTransform
from plone.transformchain.interfaces import ITransform

from seantis.dir.base.utils import cached_property
from seantis.dir.base.directory import DirectoryCatalogMixin
from seantis.dir.base.interfaces import IDirectoryRoot, IDirectoryPage
from seantis.dir.events.interfaces import IEventsDirectory

# keys for annotation
key_pageid = 'seantis.dir.events.pageid'
key_url = 'seantis.dir.events.directory_url'

# url path matching pattern
pattern = r'[~-]{1}([a-zA-Z]+)[-]?.*'


def pageid_from_name(string):
    """ Extract the pageid from a path name
    e.g. 'test' in 'https://host/test/asdf

    Return None if unsuccessful.

    """
    if not string:
        return None

    # sometimes the token ends up being quoted, even though '~' is a
    # valid character in the path segment of an url
    string = string.replace(quote('~'), '~')
    match = re.match(pattern, string)

    return match.group(1) if match else None


def urlreplace(url, **kwargs):

    parts = urlparse(url)._asdict()

    for key, value in kwargs.items():
        if callable(value):
            parts[key] = value(parts[key])
        else:
            parts[key] = kwargs[value]

    return urlunparse((
        parts['scheme'],
        parts['netloc'],
        parts['path'],
        parts['params'],
        parts['query'],
        parts['fragment']
    ))


class CustomPageRequest(object):

    """ Annotates the given request with everything that's needed to
    serve custom css / styles & content and offers methods to that effect.

    """

    def __init__(self, request):
        self.request = request
        self.annotations = IAnnotations(request)

    def hook(self, pageid, directory):
        """ Hook the request with the given pageid and the directory url. """

        self.pageid = pageid
        self.url = directory.absolute_url()

    @cached_property
    def apply_transformation(self):
        """ Return true if the urls should be transformed. """
        return bool(self.pageid and self.url)

    # the page id is used as a key to look up properties on the directory
    def get_pageid(self):
        return self.annotations.get(key_pageid)

    def set_pageid(self, pageid):
        self.annotations[key_pageid] = pageid

    pageid = property(get_pageid, set_pageid)

    # the url defines the original url of the directory which must be
    # replaced in the response body and in redirect locations
    def get_url(self):
        return self.annotations.get(key_url)

    def set_url(self, url):
        self.annotations[key_url] = url

    url = property(get_url, set_url)

    @cached_property
    def original_path(self):
        path = urlparse(self.url).path
        return path.endswith('/') and path[:-1] or path

    @cached_property
    def replacement_path(self):
        return self.original_path + '/' + self.token

    @cached_property
    def token(self):
        return '~' + self.pageid

    @cached_property
    def quoted_token(self):
        return quote(self.token)

    def transform_url(self, url):
        """ Transform the given url. """

        # if the url is already transformed, don't
        if self.token in url or self.quoted_token in url:
            return url

        return urlreplace(
            url,
            path=lambda p: p.replace(
                self.original_path, self.replacement_path, 1
            )
        )

    def properties(self, directory):
        """ Return the custom properties by page id for the given
        directory.

        """
        if not self.pageid:
            return {}

        if not hasattr(directory, self.pageid):
            return {}

        try:
            return json.loads(getattr(directory, self.pageid))
        except:
            log.exception('pageid json for %s is mal-formed' % self.pageid)

            return {}

    def custom_directory(self, directory):
        """ Return the custom directory from which title, description and
        image are loaded if a page id is found in the request.

        Returns the given directory if the custom directory cannot be found.

        """
        props = self.properties(directory)
        path = props.get('directory')

        if not path:
            return directory

        obj = getSite().unrestrictedTraverse(str(path))
        if IEventsDirectory.providedBy(obj):
            return obj
        else:
            return directory

    def custom_file(self, directory, type):
        """ Return the either the custom css or custom js file. """
        assert type in ('css', 'js')

        path = self.properties(directory).get(type)
        if not path:
            return None

        try:
            return getSite().unrestrictedTraverse(str(path))
        except NotFound:
            return None


class CustomDirectory(object):
    """ Mixin to retrieve the custom directory in instances that have the
    directory as context.

    """

    @cached_property
    def custom_directory(self):
        pagerequest = CustomPageRequest(self.request)
        return pagerequest.custom_directory(self.context)


class CustomPageHook(object):
    """ Intercepts traversal of event directories and sets up the custom
    page request if a custom token is found during traversal.

    e.g.

    'events' is the directory in the following urls:

    http://host/site/events/~custom/ => hook 'custom'
    http://host/site/events/event/~town/edit => hook 'town'
    http://host/site/~town/events/ => no hook as it is no sub-path

    """

    implements(IPublishTraverse)

    def publishTraverse(self, request, name):

        try:

            pageid = pageid_from_name(name)
            if pageid:

                pagerequest = CustomPageRequest(request)
                pagerequest.hook(pageid, self)

                return self

        except Exception:
            # Zope will consume this exception and ignore it, so
            # we log it for the record
            log.exception('error while traversing')
            raise

        return DefaultPublishTraverse(self, request).publishTraverse(
            request, name
        )


class CustomPageViewlet(grok.Viewlet, DirectoryCatalogMixin):
    """ Viewlet which renders the custom css and javascript links in the
    header. """

    grok.context(IDirectoryRoot)
    grok.name('seantis.dir.events.custom')
    grok.require('zope2.View')
    grok.viewletmanager(IHtmlHeadLinks)

    grok.order(99)  # as far below as possible

    template = grok.PageTemplateFile('templates/custom.pt')

    @cached_property
    def pagerequest(self):
        return CustomPageRequest(self.request)

    def custom_css(self):
        f = self.pagerequest.custom_file(self.context, 'css')
        return f and f.data or ''

    def custom_script(self):
        f = self.pagerequest.custom_file(self.context, 'js')
        return f and f.data or ''


class URLTransform(object):
    """ Transforms the response body, rewriting the a.href and form.action
    to include the custom page-id.

    """

    implements(ITransform)
    adapts(IDirectoryPage, IBrowserRequest)

    order = 9001

    def __init__(self, published, request):
        self.published = published
        self.request = request

    @cached_property
    def pagerequest(self):
        return CustomPageRequest(self.request)

    def transformString(self, result, encoding):
        return self.transformIterable([result], encoding)

    def transformUnicode(self, result, encoding):
        return self.transformIterable([result], encoding)

    def transformIterable(self, result, encoding):
        pagerequest = CustomPageRequest(self.request)

        if not pagerequest.apply_transformation:
            return result

        # use the tree from plone.app.theming to avoid building it ourselves
        tree = ThemeTransform(self.published, self.request).parseTree(result)
        tree = tree.tree if tree else None

        if not tree:
            return result

        # save the tree on the instance for testing, when running for real
        # plone.app.theming / diazo will take care of serializing the tree
        self._tree = tree

        path = pagerequest.original_path

        for a in tree.xpath("//a[contains(@href, '%s')]" % path):
            a.attrib['href'] = pagerequest.transform_url(
                a.attrib.get('href', '')
            )

        for form in tree.xpath("//form[contains(@action, '%s')]" % path):
            form.attrib['action'] = pagerequest.transform_url(
                form.attrib.get('action', '')
            )

        return result


@grok.subscribe(IPubSuccess)
def pub_success(e):
    """ Intercept redirects and change the location to include the custom
    page-id.

    """
    response = e.request.response
    if response.status in (301, 302, 303, 307):

        pagerequest = CustomPageRequest(e.request)
        if pagerequest.apply_transformation:
            response.setHeader(
                'Location',
                pagerequest.transform_url(response.getHeader('Location'))
            )
