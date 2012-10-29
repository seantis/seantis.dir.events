from seantis.dir.events.tests import IntegrationTestCase

class TestDateRanges(IntegrationTestCase):

    def test_events_workflow(self):

        # login to gain the right to create events
        self.login_testuser()

        # ensure that the initial state is preview
        event = self.create_event()
        self.assertEqual(self.review_state(event), 'preview')