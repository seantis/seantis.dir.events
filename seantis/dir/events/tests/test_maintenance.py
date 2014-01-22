from mock import Mock

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import maintenance


class TestMaintenance(IntegrationTestCase):

    def setUp(self):
        super(TestMaintenance, self).setUp()
        self.old_logger = maintenance.log
        maintenance.log = Mock()

    def tearDown(self):
        super(TestMaintenance, self).tearDown()
        maintenance.log = self.old_logger

    def test_register_clock_server(self):
        result = maintenance.register('method', 60 * 60)
        self.assertEquals(result.method, 'method')
        self.assertTrue('method' in maintenance._clockservers)

        maintenance.clear_clockservers()
        self.assertTrue('method' not in maintenance._clockservers)

    def test_clock_logger(self):
        logger = maintenance.ClockLogger('method')

        logger.log('GET http://localhost:888/method HTTP/1.1 200')
        self.assertEquals(0, len(maintenance.log.method_calls))

        logger.log('GET http://localhost:888/method HTTP/1.1 500')
        self.assertTrue('call.warn' in str(maintenance.log.method_calls))
        self.assertTrue('500' in str(maintenance.log.method_calls))

        logger.log('GET http://localhost:888/method HTTP/1.1')
        self.assertTrue('call.error' in str(maintenance.log.method_calls))

        logger.log('')
        self.assertEquals(3, len(maintenance.log.method_calls))

        logger.log('abcd')
        self.assertEquals(4, len(maintenance.log.method_calls))
