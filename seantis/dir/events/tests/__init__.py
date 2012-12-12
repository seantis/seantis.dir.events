import os
import unittest2 as unittest

from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from AccessControl import getSecurityManager
from plone.testing import z2
from plone.dexterity.utils import createContentInContainer
from plone.app import testing
from plone.testing.z2 import Browser
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from zope.component.hooks import getSite

from seantis.dir.events.tests.layer import INTEGRATION_TESTING
from seantis.dir.events.tests.layer import FUNCTIONAL_TESTING


class IntegrationTestCase(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        # create a default directory for events
        self.login_admin()
        self.directory = createContentInContainer(
            getSite(), 'seantis.dir.events.directory'
        )

        self.directory.manage_setLocalRoles(testing.TEST_USER_ID, ('Manager',))
        self.logout()

    def tearDown(self):
        testing.logout()

    def login_admin(self):
        """ Login as site owner (does not work with testing.login)"""
        z2.login(self.app['acl_users'], 'admin')

    def login_testuser(self):
        """ Login as test-user (does not work with z2.login)"""
        testing.login(self.portal, 'test-user')

    def logout(self):
        testing.logout()

    @property
    def workflow(self):
        return getToolByName(self.portal, "portal_workflow")

    def do_action(self, obj, action):
        self.workflow.doActionFor(obj, action)

    def create_event(self, **kw):
        """ Create an event in self.directory. By default, test-user must
        be logged in or the creation will be unauthorized.

        """

        defaults = {
            'start': datetime.today(),
            'end': datetime.today() + timedelta(seconds=60 * 60),
            'timezone': 'Europe/Zurich',
            'recurrence': ''
        }

        for attr in defaults:
            if not attr in kw:
                kw[attr] = defaults[attr]

        return createContentInContainer(
            self.directory, 'seantis.dir.events.item', **kw
        )

    def has_permission(self, obj, permission):
        return bool(getSecurityManager().checkPermission(permission, obj))

    def may_view(self, obj):
        return self.has_permission(obj, permissions.View)


class BetterBrowser(Browser):

    portal = None

    def login(self, user, password):
        self.open(self.portal.absolute_url() + "/login_form")
        self.getControl(name='__ac_name').value = user
        self.getControl(name='__ac_password').value = password
        self.getControl(name='submit').click()

        assert 'logout' in self.contents

    def logout(self):
        self.open(self.portal.absolute_url() + "/logout")

        assert 'logged out' in self.contents

    def login_admin(self):
        self.login('admin', 'secret')

    def login_testuser(self):
        self.login('test-user', 'secret')

    def assert_http_exception(self, url, exception):
        self.portal.error_log._ignored_exceptions = ()
        self.portal.acl_users.credentials_cookie_auth.login_path = ""

        expected = False
        try:
            self.open(url)
        except Exception, e:

            # zope does not always raise unathorized exceptions with the
            # correct class signature, so we need to do this thing:
            expected = e.__repr__().startswith(exception)

            if not expected:
                raise

        assert expected

    def assert_unauthorized(self, url):
        self.assert_http_exception(url, 'Unauthorized')

    def assert_notfound(self, url):
        self.assert_http_exception(url, 'NotFound')

    def show_in_browser(self):
        """ Opens the current contents in the default system browser """
        tempfile = NamedTemporaryFile(delete=False)
        tempfile.write(self.contents)
        tempfile.close()

        os.rename(tempfile.name, tempfile.name + '.html')
        os.system("open " + tempfile.name + '.html')


class FunctionalTestCase(IntegrationTestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

    def new_browser(self):
        browser = BetterBrowser(self.app)
        browser.portal = self.portal
        browser.handleErrors = False

        self.portal.error_log._ignored_exceptions = ()

        def raising(self, info):
            import traceback
            traceback.print_tb(info[2])
            print info[1]

        from Products.SiteErrorLog.SiteErrorLog import SiteErrorLog
        SiteErrorLog.raising = raising

        return browser

    def tearDown(self):
        pass
