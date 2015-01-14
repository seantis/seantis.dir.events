import os

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
from seantis.plonetools.async import clear_clockservers


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

        # Add environment variables
        os.environ['seantis_events_import'] = 'true'

        self.directory.manage_setLocalRoles(testing.TEST_USER_ID, ('Manager',))
        self.logout()

    def tearDown(self):
        clear_clockservers()
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

        # Add environment variables
        os.environ['seantis_events_import'] = 'true'

    def new_browser(self):
        return new_browser(self.layer)

    def tearDown(self):
        pass


class BrowserTestCase(FunctionalTestCase):

    def setUp(self):
        super(BrowserTestCase, self).setUp()

        self.baseurl = self.portal.absolute_url()

        browser = self.new_browser()
        browser.login_admin()

        # create an events directory
        browser.open('/++add++seantis.dir.events.directory')

        browser.getControl(name='form.widgets.title').value = 'Veranstaltungen'
        browser.getControl(
            name='form.widgets.cat1_suggestions'
        ).value = "Category1\nCategory1_2"
        browser.getControl(
            name='form.widgets.cat2_suggestions'
        ).value = "Category2\nCategory2_2"
        browser.getControl('Save').click()

        self.assertTrue('Veranstaltungen' in browser.contents)

        # the directory needs to be published for the anonymous
        # user to submit events
        browser.open(
            browser.url + '/../content_status_modify?workflow_action=publish'
        )

        self.admin_browser = browser

    def tearDown(self):
        self.admin_browser.open('/veranstaltungen/delete_confirmation')
        self.admin_browser.getControl('Delete').click()
        self.admin_browser.assert_notfound('/veranstaltungen')

    def addEvent(self, title='title', description='description',
                 cat1='Category1', cat2='Category2',
                 whole_day=False,
                 date=None, start='2:00 PM', end='4:00 PM',
                 submitter='submitter', email='submitter@example.com',
                 do_submit=True, check_submitted=True,
                 do_publish=True, check_published=True,
                 recurrence=''):

        if date is None:
            date = datetime.today()

        browser = self.admin_browser

        # Add form
        browser.open('/veranstaltungen/++add++seantis.dir.events.item')
        browser.widget('title').value = title
        browser.widget('short_description').value = description
        browser.getControl(cat1).selected = True
        browser.getControl(cat2).selected = True
        browser.widget('submission_date_type').value = ['date']
        browser.set_date('submission_date', date)
        browser.widget('submission_recurrence').value = recurrence
        if whole_day:
            browser.getControl('All day').selected = True
        else:
            browser.widget('submission_start_time').value = start
            browser.widget('submission_end_time').value = end
        browser.getControl('Continue').click()

        # Preview
        browser.getControl('Continue').click()

        if do_submit:

            # Submit
            browser.getControl(name='form.widgets.submitter').value = submitter
            browser.getControl(
                name='form.widgets.submitter_email').value = email
            browser.getControl('Submit').click()

            # Check if submitted
            if check_submitted:
                browser.open('/veranstaltungen?state=submitted' +
                             '&range=this_and_next_year')
                self.assertTrue(title in browser.contents)
                self.assertTrue(description in browser.contents)
                self.assertTrue(cat1 in browser.contents)
                self.assertTrue(cat2 in browser.contents)
            if do_publish:

                # Publish
                browser.open('/veranstaltungen?state=submitted' +
                             '&range=this_and_next_year')
                browser.getLink('Publish', index=1).click()

                # Check if published
                if check_published:
                    browser.open('/veranstaltungen?state=published' +
                                 '&range=this_and_next_year')
                    self.assertTrue(title in browser.contents)
                    self.assertTrue(description in browser.contents)
                    self.assertTrue(cat1 in browser.contents)
                    self.assertTrue(cat2 in browser.contents)
