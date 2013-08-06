from os import urandom
from uuid import UUID
from five import grok

from zope.component.hooks import getSite
from zope.component import getAdapter
from zExceptions import NotFound

from Products.CMFCore.utils import getToolByName

from seantis.dir.base.session import get_session, set_session
from seantis.dir.events.interfaces import ITokenAccess, IEventsDirectoryItem


class TokenAccess(grok.Adapter):

    grok.context(IEventsDirectoryItem)
    grok.provides(ITokenAccess)

    def attach_token(self, token=None):
        assert token != 'missing'

        self.context.access_token = token or UUID(bytes=urandom(16)).hex
        store_on_session(self.context)

    def has_access(self, request):

        if not hasattr(self.context, 'access_token'):
            return False

        token = current_token(request)
        if token == self.context.access_token:
            store_on_session(self.context)
            return True

        return False

    def clear_token(self):
        if hasattr(self.context, 'access_token'):
            del self.context.access_token

        remove_from_session()


def current_token(request):
    token = request.get('token', 'missing')

    if token == 'missing':
        try:
            token = retrieve_from_session()
        except AttributeError:
            pass

    return token.replace('-', '')


def store_on_session(context):
    assert context.access_token
    set_session(getSite(), 'events-access-token', context.access_token)


def retrieve_from_session():
    return get_session(getSite(), 'events-access-token') or 'missing'


def remove_from_session():
    set_session(getSite(), 'events-access-token', None)


def apply_token(context):
    token_access = getAdapter(context, ITokenAccess)
    token_access.attach_token()


def verify_token(context, request):
    if not context.state == 'preview':
        return

    token_access = getAdapter(context, ITokenAccess)

    if not token_access.has_access(request):
        raise NotFound()


def clear_token(context):
    token_access = getAdapter(context, ITokenAccess)
    token_access.clear_token()


def append_token(context, url):
    if not hasattr(context, 'access_token'):
        return url

    querychar = '?' if '?' not in url else '&'

    return url + querychar + 'token=' + context.access_token


def event_by_token(directory, token):

    if token == 'missing':
        return None

    catalog = getToolByName(directory, 'portal_catalog')
    path = '/'.join(directory.getPhysicalPath())

    results = catalog(path={'query': path, 'depth': 1},
        object_provides=IEventsDirectoryItem.__identifier__,
        review_state='preview',
    )

    for result in results:
        obj = result.getObject()

        if not hasattr(obj, 'access_token'):
            continue

        if obj.access_token == token:
            return obj

    return None
