from tornado import httpclient
import tornado.testing

from glinda import httpcompat
from glinda.testing import services


class ServiceUrlTests(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(ServiceUrlTests, self).setUp()
        service_layer = services.ServiceLayer()
        self.service = service_layer.get_service('service')

    def test_that_get_service_url_references_service(self):
        service_url = self.service.url_for()
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, '127.0.0.1')
        self.assertNotEqual(url.port, 0)
        self.assertEqual(url.path, '')
        self.assertEqual(url.query, '')
        self.assertEqual(url.fragment, '')

    def test_that_get_service_url_quotes_path(self):
        service_url = self.service.url_for('path that', 'needs', 'quo+ing')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.path.lower(), '/path%20that/needs/quo%2bing')

    def test_that_get_service_url_quotes_query(self):
        service_url = self.service.url_for(a='something with spaces',
                                           b='!@#$%^&*()')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(
            url.query.lower(),
            'a=something+with+spaces&b=%21%40%23%24%25%5e%26%2a%28%29'
        )

    def test_that_get_service_url_sorts_query(self):
        service_url = self.service.url_for(first=1, second=2, third=3,
                                           fini='first')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.query.lower(),
                         'fini=first&first=1&second=2&third=3')


class EndpointTests(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(EndpointTests, self).setUp()
        self.service_layer = services.ServiceLayer()

    @tornado.testing.gen_test
    def test_that_endpoint_responds_with_456_by_default(self):
        service = self.service_layer['service']
        service.add_endpoint('resource')
        client = httpclient.AsyncHTTPClient()
        try:
            yield client.fetch(service.url_for('resource'))
        except httpclient.HTTPError as error:
            self.assertEqual(error.code, 456)

    @tornado.testing.gen_test
    def test_that_endpoint_responds_with_programmed_response(self):
        service = self.service_layer['service']
        service.add_response(services.Request('GET', '/resource'),
                             services.Response(222))

        client = httpclient.AsyncHTTPClient()
        response = yield client.fetch(service.url_for('resource'))
        self.assertEqual(response.code, 222)
