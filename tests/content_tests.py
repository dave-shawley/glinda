import json
import re

from tornado import testing, web
import msgpack

from examples import contentneg
from glinda import content


KOREAN_TEXT = (u'\uc138\uacc4\ub97c \ud5a5\ud55c \ub300\ud654, '
               u'\uc720\ub2c8\ucf54\ub4dc\ub85c \ud558\uc2ed\uc2dc\uc624. '
               u'\uc81c10\ud68c \uc720\ub2c8\ucf54\ub4dc \uad6d\uc81c '
               u'\ud68c\uc758\uac00 1997\ub144 3\uc6d4 10\uc77c\ubd80\ud130 '
               u'12\uc77c\uae4c\uc9c0 \ub3c5\uc77c\uc758 \ub9c8\uc778\uc988'
               u'\uc5d0\uc11c \uc5f4\ub9bd\ub2c8\ub2e4. \uc9c0\uae08 \ub4f1'
               u'\ub85d\ud558\uc2ed\uc2dc\uc624. \uc774 \ud68c\uc758\uc5d0'
               u'\uc11c\ub294 \uc5c5\uacc4 \uc804\ubc18\uc758 \uc804\ubb38'
               u'\uac00\ub4e4\uc774 \ud568\uaed8 \ubaa8\uc5ec \ub2e4\uc74c'
               u'\uacfc \uac19\uc740 \ubd84\uc57c\ub97c \ub2e4\ub8f9\ub2c8'
               u'\ub2e4. - \uc778\ud130\ub137\uacfc \uc720\ub2c8\ucf54\ub4dc, '
               u'\uad6d\uc81c\ud654\uc640 \uc9c0\uc5ed\ud654, \uc6b4\uc601 '
               u'\uccb4\uc81c\uc640 \uc751\uc6a9 \ud504\ub85c\uadf8\ub7a8'
               u'\uc5d0\uc11c \uc720\ub2c8\ucf54\ub4dc\uc758 \uad6c\ud604, '
               u'\uae00\uaf34, \ubb38\uc790 \ubc30\uc5f4, \ub2e4\uad6d\uc5b4 '
               u'\ucef4\ud4e8\ud305.')


class JsonContentTests(testing.AsyncHTTPTestCase):

    def get_app(self):
        return web.Application([web.url('/', contentneg.HttpbinHandler)])

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
        self.assertEqual(body['headers']['Property'], 'returned in body')

    def test_that_default_charset_is_honored(self):
        response = self.fetch('/', method='POST',
                              headers={'Content-Type': 'application/json'},
                              body=b'{"name":"Andr\xC3\xA9"}')
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf-8')
        body = json.loads(response.body.decode('utf-8'))
        self.assertEqual(body['body']['name'], u'Andr\u00E9')

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


class ContentSelectionTests(testing.AsyncHTTPTestCase):

    def get_app(self):
        return web.Application([
            web.url('/', contentneg.HttpbinHandler),
            web.url('/rfc2295', contentneg.RFC2295Handler),
        ])

    def setUp(self):
        super(ContentSelectionTests, self).setUp()
        content.register_text_type('application/json', 'utf-8',
                                   json.dumps, json.loads)
        content.register_binary_type('application/msgpack', msgpack.packb,
                                     msgpack.unpackb)

    def tearDown(self):
        super(ContentSelectionTests, self).tearDown()
        content.clear_handlers()

    def test_that_simple_accept_header_is_honored(self):
        response = self.fetch('/', headers={'Accept': 'application/json'})
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf-8')
        body = json.loads(response.body.decode('utf-8'))
        self.assertEqual(body['headers']['Accept'], 'application/json')

        response = self.fetch('/', headers={'Accept': 'application/msgpack'})
        self.assertEqual(response.headers['Content-Type'],
                         'application/msgpack')
        body = msgpack.unpackb(response.body)
        self.assertEqual(body[b'headers'][b'Accept'], b'application/msgpack')

    def test_that_header_driven_translation_works(self):
        body = {'some': 'simple', 'and complex': ['body', 'elements']}
        response = self.fetch('/', method='POST', body=msgpack.packb(body),
                              headers={
                                  'Content-Type': 'application/msgpack',
                                  'Accept': 'application/json'})
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf-8')
        self.assertEqual(json.loads(response.body.decode('utf-8'))['body'],
                         body)

    def test_that_no_acceptable_content_type_raises_406(self):
        response = self.fetch('/', headers={'Accept': 'application/xml'})
        self.assertEqual(response.code, 406)

    def test_that_request_body_is_decoded_using_charset_parameter(self):
        body = u'{"value":"\u00A0\u00FF"}'
        headers = {
            'Content-Type': 'application/json; charset=latin1',
            'Accept': 'application/json',
            'Accept-Charset': 'utf8',
        }
        response = self.fetch('/', method='POST',
                              body=body.encode('latin1'),
                              headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf8')
        self.assertEqual(json.loads(response.body.decode('utf-8'))['body'],
                         json.loads(body))

    def test_that_registered_types_are_available_to_handler(self):
        # see RFC2295 section 5
        alt_pattern = re.compile(
            r'^{"[^"]*"\s+\d+(\.\d+)?\s+(?P<properties>.*)}$')
        response = self.fetch('/rfc2295', headers={'Negotiate': 'vlist',
                                                   'Accept': 'plain/text'})
        self.assertEqual(response.code, 300)
        alternatives = []
        for type_info in response.headers['Alternatives'].split(','):
            match = alt_pattern.match(type_info.strip())
            for property in re.findall('{[^}]*}', match.group('properties')):
                name, value = property[1:-1].split(' ', 1)
                if name == 'type':
                    alternatives.append(value)
        self.assertEqual(sorted(alternatives),
                         ['application/json', 'application/msgpack'])


class TextEncodingTests(testing.AsyncHTTPTestCase):

    @staticmethod
    def unicode_dumper(body, **kwargs):
        kwargs['ensure_ascii'] = True
        return json.dumps(body, **kwargs)

    def get_app(self):
        return web.Application([web.url('/', contentneg.HttpbinHandler)])

    def setUp(self):
        super(TextEncodingTests, self).setUp()
        content.register_text_type('application/json', 'utf-8',
                                   self.unicode_dumper, json.loads)

    def tearDown(self):
        super(TextEncodingTests, self).tearDown()
        content.clear_handlers()

    def test_that_accept_charset_is_honored(self):
        str_body = json.dumps({'text': KOREAN_TEXT})
        encoded_body = str_body.encode('utf-8')
        response = self.fetch('/', body=encoded_body, method='POST', headers={
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Charset': 'euc_kr',
        })
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=euc_kr')
        self.assertEqual(json.loads(response.body.decode('euc_kr'))['body'],
                         {'text': KOREAN_TEXT})

    def test_that_unknown_encoding_raises_406(self):
        response = self.fetch('/', headers={'Accept-Charset': 'foo'})
        self.assertEqual(response.code, 406)
