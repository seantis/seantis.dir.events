import re

from seantis.dir.events.tests import FunctionalTestCase

class BrowserTestCase(FunctionalTestCase):

    def test_event_submission(self):
        
        baseurl = self.portal.absolute_url()

        browser = self.new_browser()
        browser.login_admin()

        # create an events directory
        browser.open(baseurl + '/++add++seantis.dir.events.directory')
        
        browser.getControl('Name').value = 'Veranstaltungen'
        browser.getControl('Save').click()

        self.assertTrue('Veranstaltungen' in browser.contents)

        # the directory needs to be published for the anonymous
        # user to submit events
        browser.open(browser.url + '/../content_status_modify?workflow_action=publish')

        # get a browser for anonymous
        fourchan = self.new_browser()
        fourchan.open(baseurl + '/veranstaltungen')

        self.assertTrue('Veranstaltungen' in browser.contents)

        # get to the submit form
        fourchan.getLink('Submit Your Event').click()

        self.assertTrue('Send us your events' in fourchan.contents)

        fourchan.getControl(name='form.widgets.title').value = 'Stammtisch'
        fourchan.getControl(name='form.widgets.short_description').value = 'Socializing Yo'
        
        fourchan.getControl('Preview Event').click()

        # previewing an event should send us to the preview view
        self.assertTrue('preview-event' in fourchan.url)

        # a token should have been added to the url
        self.assertTrue('token=' in fourchan.url)

        # the preview should contain the entered information
        self.assertTrue('Socializing Yo' in fourchan.contents)

        # there's a change-event button which can't be found by getControl
        # which contains onclick javascript code as well as a data attribute
        # with the url of the button

        edit_url = re.search('data-url="(.*?)"', fourchan.contents).groups()[0]
        self.assertTrue('edit-event' in edit_url)

        # we should be able to go back to the edit form, change some things
        # and come back to the url to find those changes

        fourchan.open(edit_url)
        fourchan.getControl(name='form.widgets.short_description').value = 'Serious Business'
        fourchan.getControl('Update Event Preview').click()

        self.assertTrue('Serious Business' in fourchan.contents)
        self.assertTrue('preview-event' in fourchan.url)

        # at the same time this event in preview is invisble in the list
        # even for administrators
        browser.open(baseurl + '/veranstaltungen')
        self.assertTrue('Veranstaltungen' in browser.contents)
        self.assertFalse('Serious Business' in browser.contents)

        # other anonymous users may not access the view or the preview
        google_robot = self.new_browser()
        google_robot.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch')
        google_robot.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch/preview-event')

        # not event the admin at this point (not sure about that one yet)
        browser.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch')
        browser.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch/preview-event')

        # if the user decides to cancel the event before submitting it, he
        # loses the right to access the event (will be cleaned up by cronjob)
        fourchan.getControl('Cancel Event Submission').click()

        fourchan.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch')
        fourchan.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch/preview-event')
        fourchan.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch/edit-event')

        # since we cancelled we must now create a new event to
        # test the submission process
        new = self.new_browser()
        new.open(baseurl + '/veranstaltungen/submit-event')

        new.getControl(name='form.widgets.title').value = "Submitted Event"
        new.getControl(name='form.widgets.short_description').value = "YOLO"

        new.getControl('Preview Event').click()

        # at this point the event is invisble to the admin
        browser.open(baseurl + '/veranstaltungen')
        self.assertFalse('YOLO' in browser.contents)

        # until the anonymous user submits the event
        new.getControl('Submit Event').click()
        browser.open(baseurl + '/veranstaltungen')
        self.assertTrue('YOLO' in browser.contents)

        # the user may no longer access the event at this point
        new.assert_unauthorized(baseurl + '/veranstaltungen/submitted-event')
