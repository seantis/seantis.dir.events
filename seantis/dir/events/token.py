from uuid import UUID
from five import grok

from AccessControl.unauthorized import Unauthorized
from zope.component import getAdapter

from M2Crypto.m2 import rand_bytes

from zExceptions import NotFound

from seantis.dir.base.session import get_session, set_session
from seantis.dir.events.interfaces import ITokenAccess, IEventsDirectoryItem

class TokenAccess(grok.Adapter):

    grok.context(IEventsDirectoryItem)
    grok.provides(ITokenAccess)

    def attach_token(self, token=None):
        assert token != 'missing'

        self.context.access_token = token or UUID(bytes=rand_bytes(16)).hex
        self.store_on_session()

    def has_access(self, request):

        if not hasattr(self.context, 'access_token'):
            return False

        request_token = request.get('token', 'missing')
        request_token = request_token.replace('-', '')

        if request_token == self.context.access_token:
            self.store_on_session()
            return True

        session_token = self.retrieve_from_session()
        return session_token == self.context.access_token

    def store_on_session(self):
        assert self.context.access_token
        set_session(self.context, 'events-access-token', self.context.access_token)

    def retrieve_from_session(self):
        return get_session(self.context, 'events-access-token') or 'missing'

    def remove_from_session(self):
        set_session(self.context, 'events-access-token', None)

    def clear_token(self):
        if hasattr(self.context, 'access_token'):
            del self.context.access_token
        
        self.remove_from_session()

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