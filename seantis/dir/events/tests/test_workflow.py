from Products.CMFCore.WorkflowCore import WorkflowException
from zope.interface import alsoProvides

from seantis.dir.events.interfaces import IExternalEvent
from seantis.dir.events.tests import IntegrationTestCase


class TestWorkflow(IntegrationTestCase):

    def setUp(self):
        super(TestWorkflow, self).setUp()
        # login to gain the right to create events
        self.login_testuser()

    def tearDown(self):
        super(TestWorkflow, self).tearDown()
        self.logout()

    def test_events_workflow(self):

        # ensure that the initial state is preview
        event = self.create_event()
        self.assertEqual(event.state, 'preview')

        # go through the states
        event.submit()
        self.assertEqual(event.state, 'submitted')

        event.deny()
        self.assertEqual(event.state, 'archived')

        event = self.create_event()
        self.assertEqual(event.state, 'preview')

        event.submit()
        self.assertEqual(event.state, 'submitted')

        event.publish()
        self.assertEqual(event.state, 'published')

        event.archive()
        self.assertEqual(event.state, 'archived')

        event.publish()
        self.assertEqual(event.state, 'published')

        event.archive()
        self.assertEqual(event.state, 'archived')

        event.archive_permanently()
        self.assertEqual(event.state, 'archived_permanently')

        event.publish()
        self.assertEqual(event.state, 'published')

        alsoProvides(event, IExternalEvent)

        event.hide()
        self.assertEqual(event.state, 'hidden')

        event.publish()
        self.assertEqual(event.state, 'published')

        # try some impossible changes
        event = self.create_event()
        action = lambda a: event.do_action(a)

        self.assertRaises(WorkflowException, action, 'archive')
        self.assertRaises(WorkflowException, action, 'archive_permanently')
        self.assertRaises(WorkflowException, action, 'deny')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'publish')

        event.submit()

        self.assertRaises(WorkflowException, action, 'archive')
        self.assertRaises(WorkflowException, action, 'archive_permanently')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'submit')

        event.publish()

        self.assertRaises(WorkflowException, action, 'archive_permanently')
        self.assertRaises(WorkflowException, action, 'deny')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'publish')
        self.assertRaises(WorkflowException, action, 'submit')

        event.archive()

        self.assertRaises(WorkflowException, action, 'archive')
        self.assertRaises(WorkflowException, action, 'deny')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'submit')

        event.archive_permanently()

        self.assertRaises(WorkflowException, action, 'archive')
        self.assertRaises(WorkflowException, action, 'deny')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'submit')

        event.publish()
        alsoProvides(event, IExternalEvent)
        event.hide()

        self.assertRaises(WorkflowException, action, 'archive')
        self.assertRaises(WorkflowException, action, 'deny')
        self.assertRaises(WorkflowException, action, 'hide')
        self.assertRaises(WorkflowException, action, 'submit')

    def test_access_guard(self):

        # normal events
        event = self.create_event()
        allow = ['submit', 'publish', 'deny', 'archive']
        deny = ['hide']
        for action in allow:
            self.assertTrue(event.allow_action(action))
        for action in deny:
            self.assertFalse(event.allow_action(action))

        # imported events
        alsoProvides(event, IExternalEvent)
        allow = ['hide', 'publish']
        deny = ['submit', 'deny', 'archive']
        for action in allow:
            self.assertTrue(event.allow_action(action))
        for action in deny:
            self.assertFalse(event.allow_action(action))

        # use a custom guard to ensure that the guards are actually
        # set in the definition xml file
        event = self.create_event()
        action = lambda a: event.do_action(a)

        event.allow_action = lambda a: False

        self.assertRaises(WorkflowException, action, 'submit')

        event.allow_action = lambda a: True

        action('submit')
