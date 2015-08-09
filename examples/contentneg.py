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
from tornado import httpserver, ioloop, web

# The following will be supported if available
def maybe_import(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None

msgpack = maybe_import('msgpack')
yaml = maybe_import('yaml')


class HttpbinHander(content.HandlerMixin, web.RequestHandler):
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

    app = web.Application([web.url(r'/', HttpbinHander)], debug=True)
    server = httpserver.HTTPServer(app)
    server.listen(int(os.environ.get('PORT', '8000')))
    iol = ioloop.IOLoop.instance()
    try:
        ioloop.IOLoop.instance().start()
        iol.start()
    except KeyboardInterrupt:
        logging.info('stopping application')
        iol.add_callback(iol.stop)
