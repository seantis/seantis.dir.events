import transaction

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

from Testing import ZopeTestCase as ztc
from OFS.Folder import Folder


class Fixture(PloneSandboxLayer):

    default_bases = (PLONE_FIXTURE, )

    class Session(dict):
        def set(self, key, value):
            self[key] = value

    def setUpZope(self, app, configurationContext):

        import seantis.dir.events
        self.loadZCML(package=seantis.dir.events)

        app.REQUEST['SESSION'] = self.Session()

        if not hasattr(app, 'temp_folder'):
            app._setObject('temp_folder', Folder('temp_folder'))
            transaction.commit()
            ztc.utils.setupCoreSessions(app)

    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'seantis.dir.events:default')

        # should probably go to metadata.xml
        self.applyProfile(portal, 'plone.app.event:default')
        self.applyProfile(portal, 'collective.geo.geographer:default')
        self.applyProfile(portal, 'collective.geo.mapwidget:default')
        self.applyProfile(portal, 'collective.geo.contentlocations:default')
        self.applyProfile(portal, 'collective.geo.kml:default')
        self.applyProfile(portal, 'collective.geo.settings:default')

FIXTURE = Fixture()
INTEGRATION_TESTING = IntegrationTesting(
    bases=(FIXTURE,),
    name='seantis.dir.events:Integration'
)
FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FIXTURE,),
    name='seantis.dir.events:Functional'
)
