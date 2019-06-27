import unittest

from tornado import httpclient
import tornado.testing

from glinda import httpcompat
from glinda.testing import services


class ServiceUrlTests(unittest.TestCase):

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
        self.assertEqual(url.path, '/')
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
        service.add_response(services.Request('GET', '/resource:test'),
                             services.Response(222))

        client = httpclient.AsyncHTTPClient()
        response = yield client.fetch(service.url_for('resource:test'))
        self.assertEqual(response.code, 222)

    @tornado.testing.gen_test
    def test_that_empty_path_is_usable(self):
        service = self.service_layer['service']
        service.add_response(services.Request('GET', '/'),
                             services.Response(222))

        client = httpclient.AsyncHTTPClient()
        response = yield client.fetch(service.url_for('/'))
        self.assertEqual(response.code, 222)

    @tornado.testing.gen_test
    def test_that_error_handler_works(self):
        service = self.service_layer['service']

        client = httpclient.AsyncHTTPClient()
        response = yield client.fetch(service.url_for('/'), raise_error=False)
        self.assertEqual(response.code, 456)


class RequestRecordingTests(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(RequestRecordingTests, self).setUp()
        self.service_layer = services.ServiceLayer()

    @tornado.testing.gen_test
    def test_that_all_request_details_are_recorded(self):
        service = self.service_layer['service']
        service.add_response(services.Request('POST', '/resource'),
                             services.Response(200))

        url = service.url_for('/resource', arg='value', arg2='value')
        client = httpclient.AsyncHTTPClient()
        yield client.fetch(url, method='POST', body='BODY',
                           headers={'Custom': 'Header'})
        req = next(service.get_requests_for('/resource'))
        self.assertEqual(req.method, 'POST')
        self.assertEqual(req.resource, '/resource')
        self.assertEqual(req.query, {'arg': 'value', 'arg2': 'value'})
        self.assertEqual(req.body, b'BODY')
        self.assertEqual(req.headers['Custom'], 'Header')
        self.assertIn('Host', req.headers)  # always present in HTTP/1.1

    def test_that_get_request_for_asserts_without_requests(self):
        service = self.service_layer['service']
        with self.assertRaises(AssertionError):
            next(service.get_requests_for('/whatever'))

    def test_that_get_request_asserts_without_requests(self):
        service = self.service_layer['service']
        with self.assertRaises(AssertionError):
            service.get_request('/whatever')

    @tornado.testing.gen_test
    def test_that_assert_request_fails_for_incorrect_request(self):
        service = self.service_layer['service']
        service.add_response(services.Request('GET', '/resource'),
                             services.Response(200))

        client = httpclient.AsyncHTTPClient()
        yield client.fetch(service.url_for('/resource', one='1', two=2))
        with self.assertRaises(AssertionError):
            service.assert_request('GET', '/resource')

    @tornado.testing.gen_test
    def test_that_assert_request_matches_all_parameters(self):
        service = self.service_layer['service']
        service.add_response(services.Request('GET', '/resource'),
                             services.Response(200))
        service.add_response(services.Request('POST', '/resource'),
                             services.Response(200))

        client = httpclient.AsyncHTTPClient()
        yield client.fetch(service.url_for('/resource', foo='bar'),
                           method='POST', body='')
        with self.assertRaises(AssertionError):
            service.assert_request('GET', '/resource', foo='bar')
        service.assert_request('POST', '/resource', foo='bar')
