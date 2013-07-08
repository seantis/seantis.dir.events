import unittest2 as unittest

from datetime import datetime, timedelta

from AccessControl import getSecurityManager
from plone.testing import z2
from plone.dexterity.utils import createContentInContainer
from plone.app import testing
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from collective.betterbrowser import new_browser

from zope.component import getAdapter
from zope.component.hooks import getSite

from seantis.dir.base.interfaces import IDirectoryCatalog
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
        self.catalog = getAdapter(self.directory, IDirectoryCatalog)

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


class FunctionalTestCase(IntegrationTestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

    def new_browser(self):
        return new_browser(self.layer)

    def tearDown(self):
        pass
