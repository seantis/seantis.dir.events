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
        
        fourchan.getControl('Save').click()

        # we should've been redirected at this point
        self.assertTrue(fourchan.url.endswith('veranstaltungen'))

        # and we should be able to open the view
        fourchan.open(fourchan.url + '/stammtisch')

        # and make changes to the item
        fourchan.open(fourchan.url + '/edit-event')
        fourchan.getControl(name='form.widgets.short_description').value = 'Serious Business'
        fourchan.getControl('Save').click()

        self.assertFalse('edit-event' in fourchan.url)
        self.assertTrue('Serious Business' in fourchan.contents)

        # at the same time this event in preview is invisble in the list
        # even for administrators
        browser.open(baseurl + '/veranstaltungen')
        self.assertTrue('Veranstaltungen' in browser.contents)
        self.assertFalse('Serious Business' in browser.contents)

        # other anonymous users may not access the view
        google_robot = self.new_browser()
        google_robot.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch')

        # not event the admin at this point (not sure about that one yet)
        browser.assert_unauthorized(baseurl + '/veranstaltungen/stammtisch')