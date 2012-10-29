from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting

class Fixture(PloneSandboxLayer):

    default_bases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):

        import seantis.dir.events
        self.loadZCML(package=seantis.dir.events)

    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'seantis.dir.events:default')
        self.applyProfile(portal, 'plone.app.event:default')

FIXTURE = Fixture()
INTEGRATION_TESTING = IntegrationTesting(
    bases=(FIXTURE,),
    name='seantis.dir.events:Integration'
)