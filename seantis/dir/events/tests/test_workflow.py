from seantis.dir.events.tests import IntegrationTestCase
from Products.CMFCore.WorkflowCore import WorkflowException


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
        event.do_action('submit')
        self.assertEqual(event.state, 'submitted')

        event.do_action('publish')
        self.assertEqual(event.state, 'published')

        event.do_action('archive')
        self.assertEqual(event.state, 'archived')

        event.do_action('publish')
        self.assertEqual(event.state, 'published')

        # try some impossible changes
        event = self.create_event()
        action = lambda a: event.do_action(a)

        self.assertRaises(WorkflowException, action, 'publish')
        self.assertRaises(WorkflowException, action, 'archive')

        event.do_action('submit')

        self.assertRaises(WorkflowException, action, 'archive')

        event.do_action('publish')

        self.assertRaises(WorkflowException, action, 'submit')

        event.do_action('archive')

        self.assertRaises(WorkflowException, action, 'submit')

        # try denying an event (skipping the publication)
        event = self.create_event()

        event.do_action('submit')
        self.assertEqual(event.state, 'submitted')

        event.do_action('deny')
        self.assertEqual(event.state, 'archived')

    def test_access_guard(self):
        actions = ['submit', 'publish', 'deny', 'archive']

        # the default access guard has no limits
        event = self.create_event()

        for action in actions:
            self.assertTrue(event.allow_action(action))

        # use a custom guard to ensure that the guards are actually
        # set in the definition xml file
        event = self.create_event()
        action = lambda a: event.do_action(a)

        event.allow_action = lambda a: False

        self.assertRaises(WorkflowException, action, 'submit')

        event.allow_action = lambda a: True

        action('submit')
