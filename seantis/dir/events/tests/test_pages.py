from zope.publisher.browser import TestRequest
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import directlyProvides

from repoze.xmliter.serializer import XMLSerializer

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events import pages


class PagesTestCase(IntegrationTestCase):

    def test_stringmatching(self):
        match = pages.pageid_from_string

        self.assertEqual(match('https://google.com'), None)
        self.assertEqual(match('https://google.com/test'), None)
        self.assertEqual(match('https://host/~test'), 'test')
        self.assertEqual(match('https://host/-test-'), 'test')

        self.assertEqual(match('~id'), 'id')
        self.assertEqual(match('-id-'), 'id')
        self.assertEqual(match(None), None)
        self.assertEqual(match(''), None)
        self.assertEqual(match('~/-test'), 'test')
        self.assertEqual(match('~~~asdf'), 'asdf')

    def test_urltransform(self):
        request = TestRequest()
        directlyProvides(request, IAttributeAnnotatable)

        request.response.setHeader('Content-Type', 'text/html')

        custom = pages.CustomPageRequest(request)
        custom.hook('custompage', self.directory)

        transform = pages.URLTransform(self.directory, request)

        def run(s):
            transform.transformString(s, 'ascii')

            if hasattr(transform, '_tree'):
                return str(XMLSerializer(transform._tree))

            return None

        html = """
        <html>
            <head></head>
            <body>
                <a href="%(url)s"></a>
                <a href="#"></a>
                <form action="%(url)s"></form>
                <form></form>
            </body>
        </html>
        """ % dict(url=self.directory.absolute_url())

        result = run(html)

        url = self.directory.absolute_url() + '/~custompage'
        self.assertEqual(result.count(url), 2)

        replaced = '"%s"' % self.directory.absolute_url()
        self.assertEqual(result.count(replaced), 0)
