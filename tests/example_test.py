"""
Example of using glinda to test a service.

This file is an example of using the ``glinda.testing`` package to
test a very simple Tornado application.

"""
import os

from tornado import gen, httpclient, web
import tornado.testing

from glinda.testing import services


class MyHandler(web.RequestHandler):
    """
    Simple handler that makes a few asynchronous requests.

    The "backing" service is configured by setting the ``SERVICE_NETLOC``
    environment variable to the host and port of the service endpoint.
    This is pretty typical for 12 Factor Applications and it makes it
    very easy to test the service using ``glinda``.

    """

    @gen.coroutine
    def get(self):
        netloc = os.environ['SERVICE_NETLOC']
        client = httpclient.AsyncHTTPClient()
        try:
            yield client.fetch('http://{0}/status'.format(netloc),
                               method='HEAD')
        except web.HTTPError as error:
            if error.code >= 300:
                raise web.HTTPError(504)

        try:
            response = yield client.fetch('http://{0}/do-stuff'.format(netloc),
                                          method='POST',
                                          body='important stuff')
        except web.HTTPError as error:
            if error.code >= 300:
                raise web.HTTPError(500)

        self.set_status(200)
        self.set_header('Custom', response.headers.get('Custom', ''))
        self.write(response.body)
        self.finish()


class HandlerTests(tornado.testing.AsyncHTTPTestCase):
    """Traditional :class:`tornado.testing.AsyncHTTPTestCase`"""

    def setUp(self):
        super(HandlerTests, self).setUp()
        service_layer = services.ServiceLayer()
        self.external_service = service_layer['status']
        os.environ['SERVICE_NETLOC'] = self.external_service.host

    def get_app(self):
        return web.Application([web.url('/do-the-things', MyHandler)])

    def test_that_status_failure_results_in_504(self):
        self.external_service.add_response(
            services.Request('HEAD', '/status'), services.Response(500))
        try:
            self.fetch('/do-the-things')
        except web.HTTPError as error:
            self.assertEqual(error.status_code, 504)

    def test_that_service_failure_results_in_500(self):
        self.external_service.add_response(
            services.Request('HEAD', '/status'), services.Response(200))
        self.external_service.add_response(
            services.Request('POST', '/do-stuff'), services.Response(400))
        try:
            self.fetch('/do-the-things')
        except web.HTTPError as error:
            self.assertEqual(error.status_code, 500)

    def test_that_status_is_fetched(self):
        self.external_service.add_response(
            services.Request('HEAD', '/status'), services.Response(200))
        self.external_service.add_response(
            services.Request('POST', '/do-stuff'), services.Response(200))
        self.fetch('/do-the-things')
        self.external_service.assert_request('HEAD', '/status')

    def test_that_stuff_is_posted(self):
        self.external_service.add_response(
            services.Request('HEAD', '/status'), services.Response(200))
        self.external_service.add_response(
            services.Request('POST', '/do-stuff'), services.Response(200))
        self.fetch('/do-the-things')

        request = self.external_service.get_request('do-stuff')
        self.assertEqual(request.body, b'important stuff')

    def test_that_post_response_is_preserved(self):
        self.external_service.add_response(
            services.Request('HEAD', '/status'), services.Response(200))
        self.external_service.add_response(
            services.Request('POST', '/do-stuff'),
            services.Response(200, body='foo', headers={'Custom': 'header'}))

        response = self.fetch('/do-the-things')
        self.assertEqual(response.body.decode(), 'foo')
        self.assertEqual(response.headers['Custom'], 'header')
