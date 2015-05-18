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
        response = yield client.fetch('http://{0}/status'.format(netloc),
                                      method='HEAD', raise_error=False)
        if response.code >= 300:
            raise web.HTTPError(504)

        response = yield client.fetch('http://{0}/do-stuff'.format(netloc),
                                      method='POST', raise_error=False)
        if response.code >= 300:
            raise web.HTTPError(500)

        self.set_status(200)
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
