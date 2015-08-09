#!/usr/bin/env python
"""

Example tornado application that handles content negotiation.

This is an example of using glinda's content negotiation functionality
in a simple Tornado application.

"""
import importlib
import json
import logging
import os

from glinda import content, httpcompat
from ietfparse import headers
from tornado import httpserver, ioloop, web


# The following will be supported if available
def maybe_import(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None

msgpack = maybe_import('msgpack')
yaml = maybe_import('yaml')


class HttpbinHandler(content.HandlerMixin, web.RequestHandler):
    """Mimics http://httpbin.org/{get,post}"""

    def get(self):
        self.send_response(self.standard_response_dict)
        self.finish()

    def post(self):
        response = self.standard_response_dict
        response['data'] = repr(self.request.body)
        response['files'] = {}
        response['form'] = {}
        response['body'] = self.get_request_body()
        self.send_response(response)
        self.finish()

    @property
    def standard_response_dict(self):
        return {
            'args': httpcompat.parse_qs(self.request.query),
            'headers': dict(self.request.headers),
            'origin': self.request.remote_ip,
            'url': self.request.uri,
        }


class RFC2295Handler(content.HandlerMixin, web.RequestHandler):
    """Implements a bare-bones version of RFC2295 Negotiation."""

    def prepare(self):
        super(RFC2295Handler, self).prepare()
        if not self._finished:
            negotiate = headers.parse_list_header(
                self.request.headers.get('Negotiate', ''))
            if 'vlist' in negotiate:
                variants = []
                for content_type in self.registered_content_types:
                    variants.append('{{"{0}" 1.0 {{type {1}}}}}'.format(
                        self.request.uri, content_type))
                self.set_header('Alternatives', ', '.join(variants))
                self.set_header('TCN', 'list')

    def send_response(self, response_dict):
        try:
            super(RFC2295Handler, self).send_response(response_dict)
        except web.HTTPError as error:
            if error.status_code == 406:
                self.set_status(300, 'Multiple Choices')
                self.set_header('Vary', 'negotiate, accept')
                return
            raise

    def get(self):
        self.send_response({'hi': 'there'})


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)1.1s %(name)s: %(message)s')
    content.register_text_type('application/json', 'utf-8',
                               dumper=json.dumps, loader=json.loads)
    if msgpack:
        content.register_binary_type('application/x-msgpack',
                                     dumper=msgpack.packb,
                                     loader=msgpack.unpackb)
    if yaml:
        content.register_text_type('application/yaml', 'utf-8',
                                   dumper=yaml.dump, loader=yaml.load)

    app = web.Application([
        web.url(r'/', HttpbinHandler),
        web.url(r'/negotiate', RFC2295Handler),
    ], debug=True)
    server = httpserver.HTTPServer(app)
    server.listen(int(os.environ.get('PORT', '8000')))
    iol = ioloop.IOLoop.instance()
    try:
        ioloop.IOLoop.instance().start()
        iol.start()
    except KeyboardInterrupt:
        logging.info('stopping application')
        iol.add_callback(iol.stop)
