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
        self.do_action(event, 'submit')
        self.assertEqual(event.state, 'submitted')

        self.do_action(event, 'publish')
        self.assertEqual(event.state, 'published')

        self.do_action(event, 'archive')
        self.assertEqual(event.state, 'archived')

        self.do_action(event, 'publish')
        self.assertEqual(event.state, 'published')

        # try some impossible changes
        event = self.create_event()
        action = lambda a: self.do_action(event, a)

        self.assertRaises(WorkflowException, action, ['publish'])
        self.assertRaises(WorkflowException, action, ['archive'])

        self.do_action(event, 'submit')

        self.assertRaises(WorkflowException, action, ['archive'])        

        self.do_action(event, 'publish')

        self.assertRaises(WorkflowException, action, ['submit'])

        self.do_action(event, 'archive')

        self.assertRaises(WorkflowException, action, ['submit'])