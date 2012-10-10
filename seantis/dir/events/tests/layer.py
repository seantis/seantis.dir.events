from Products.PloneTestCase import ptc
import collective.testcaselayer.ptc

ptc.setupPloneSite()

class IntegrationTestLayer(collective.testcaselayer.ptc.BasePTCLayer):

    def afterSetUp(self):
        self.addProfile('seantis.dir.events:default')
        self.addProfile('plone.app.event:default')

Layer = IntegrationTestLayer([collective.testcaselayer.ptc.ptc_layer])