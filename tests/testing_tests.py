from tornado import httpclient
import tornado.testing

from glinda import httpcompat
from glinda.testing import services


class ServiceUrlTests(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(ServiceUrlTests, self).setUp()
        self.service_layer = services.ServiceLayer()
        self.service_layer.add_endpoint('service')

    def test_that_get_service_url_references_service(self):
        service_url = self.service_layer.get_service_url('service')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, '127.0.0.1')
        self.assertNotEqual(url.port, 0)
        self.assertEqual(url.path, '')
        self.assertEqual(url.query, '')
        self.assertEqual(url.fragment, '')

    def test_that_get_service_url_quotes_path(self):
        service_url = self.service_layer.get_service_url(
            'service', 'path that', 'needs', 'quo+ing')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.path.lower(), '/path%20that/needs/quo%2bing')

    def test_that_get_service_url_quotes_query(self):
        service_url = self.service_layer.get_service_url(
            'service', a='something with spaces', b='!@#$%^&*()')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(
            url.query.lower(),
            'a=something+with+spaces&b=%21%40%23%24%25%5e%26%2a%28%29'
        )

    def test_that_get_service_url_sorts_query(self):
        service_url = self.service_layer.get_service_url(
            'service', first=1, second=2, third=3, fini='first')
        url = httpcompat.urlsplit(service_url)
        self.assertEqual(url.query.lower(),
                         'fini=first&first=1&second=2&third=3')


class EndpointTests(tornado.testing.AsyncTestCase):

    @tornado.testing.gen_test
    def test_that_endpoint_responds(self):
        service_layer = services.ServiceLayer()
        service_layer.add_endpoint('service', 'resource')
        client = httpclient.AsyncHTTPClient()
        try:
            yield client.fetch(
                service_layer.get_service_url('service', 'resource'))
        except httpclient.HTTPError as error:
            self.assertEqual(error.code, 405)
