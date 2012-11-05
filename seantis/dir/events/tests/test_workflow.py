from seantis.dir.events.tests import IntegrationTestCase
from Products.CMFCore.WorkflowCore import WorkflowException

class TestDateRanges(IntegrationTestCase):

    def test_events_workflow(self):

        # login to gain the right to create events
        self.login_testuser()

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

        self.assertRaises(WorkflowException, action, ['publish'])
        self.assertRaises(WorkflowException, action, ['archive'])

        event.do_action('submit')

        self.assertRaises(WorkflowException, action, ['archive'])        

        event.do_action('publish')

        self.assertRaises(WorkflowException, action, ['submit'])

        event.do_action('archive')

        self.assertRaises(WorkflowException, action, ['submit'])

        # try denying an event (skipping the publication)

        event = self.create_event()
    
        event.do_action('submit')
        self.assertEqual(event.state, 'submitted')

        event.do_action('deny')
        self.assertEqual(event.state, 'archived')