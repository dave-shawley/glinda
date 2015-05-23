import json

from tornado import testing, web

from glinda import content


class SimpleHandler(content.HandlerMixin, web.RequestHandler):

    def get(self):
        self.send_response(self.request.headers)
        self.finish()

    def post(self, *args, **kwargs):
        self.send_response(self.request_body)
        self.finish()


class JsonContentTests(testing.AsyncHTTPTestCase):

    def get_app(self):
        return web.Application([web.url('/', SimpleHandler)])

    def setUp(self):
        super(JsonContentTests, self).setUp()
        content.register_text_type('application/json', 'utf-8',
                                   json.dumps, json.loads)

    def tearDown(self):
        super(JsonContentTests, self).tearDown()
        content.clear_handlers()

    def test_that_response_uses_registered_encoder(self):
        response = self.fetch('/', headers={'Property': 'returned in body'})
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf-8')
        body = json.loads(response.body.decode('utf-8'))
        self.assertEqual(body['Property'], 'returned in body')

    def test_that_default_charset_is_honored(self):
        response = self.fetch('/', method='POST',
                              headers={'Content-Type': 'application/json'},
                              body=b'{"name":"Andr\xC3\xA9"}')
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf-8')
        body = json.loads(response.body.decode('utf-8'))
        self.assertEqual(body, {'name': u'Andr\u00E9'})

    def test_that_body_decode_failure_results_in_client_error(self):
        response = self.fetch('/', method='POST',
                              headers={'Content-Type': 'application/json'},
                              body=b'not json')
        self.assertEqual(response.code, 400)

    def test_that_unknown_content_type_results_in_unsupp_media_type(self):
        response = self.fetch('/', method='POST',
                              headers={'Content-Type': 'application/xml'},
                              body=b'<?xml version="1.0"?><body/>')
        self.assertEqual(response.code, 415)
