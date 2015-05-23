from ietfparse import algorithms, headers, errors
from tornado import web


class _ContentHandler(object):

    def __init__(self):
        super(_ContentHandler, self).__init__()
        self.dumps, self.loads = None, None
        self.default_encoding = None

    def unpack_bytes(self, obj_bytes, encoding=None):
        return self.loads(obj_bytes.decode(encoding or self.default_encoding))

    def pack_bytes(self, obj_dict, encoding=None):
        encoding = encoding or self.default_encoding
        return encoding, self.dumps(obj_dict).encode(encoding)


_content_handlers = {}
_content_types = {}


def register_text_type(content_type, default_encoding, dumper, loader):
    """
    Register handling for a text-based content type.

    :param str content_type: content type to register the hooks for
    :param str default_encoding: encoding to use if none is present
        in the request
    :param dumper: called to decode a string into a dictionary.
        Calling convention: ``dumper(obj_dict).encode(encoding) -> bytes``
    :param loader: called to encode a dictionary to a string.
        Calling convention: ``loader(obj_bytes.decode(encoding)) -> dict``

    The decoding of a text content body takes into account decoding
    the binary request body into a string before calling the underlying
    dump/load routines.

    """
    content_type = headers.parse_content_type(content_type)
    key = str(content_type)
    _content_types[key] = content_type

    handler = _content_handlers.setdefault(key, _ContentHandler())
    handler.dumps = dumper or handler.dumps
    handler.loads = loader or handler.loads
    handler.default_encoding = default_encoding or handler.default_encoding


def clear_handlers():
    """Clears registered type handlers."""
    _content_handlers.clear()
    _content_types.clear()


class HandlerMixin(object):
    """
    Mix this in over ``RequestHandler`` to enable content handling.
    """

    def __init__(self, *args, **kwargs):
        super(HandlerMixin, self).__init__(*args, **kwargs)
        self._request_body = None

    @property
    def request_body(self):
        """The decoded request body."""
        if self._request_body is None:
            content_type_str = self.request.headers.get(
                'Content-Type', 'application/octet-stream')
            content_type = headers.parse_content_type(content_type_str)
            content_type.quality = 1  # TODO FIXME
            try:
                selected, requested = algorithms.select_content_type(
                    [content_type], _content_types.values())
            except errors.NoMatch:
                raise web.HTTPError(
                    415, 'cannot decoded content type %s', content_type_str,
                    reason='Unexpected content type')
            handler = _content_handlers[str(selected)]
            try:
                self._request_body = handler.unpack_bytes(self.request.body)
            except ValueError as error:
                raise web.HTTPError(
                    400, 'failed to decode content body - %r', error,
                    reason='Content body decode failure')
        return self._request_body

    def send_response(self, response_dict):
        """
        Encode a response according to the request.

        :param dict response_dict:

        """
        accept = headers.parse_http_accept_header(self.request.headers.get('Accept', '*/*'))
        selected, _ = algorithms.select_content_type(accept, _content_types.values())
        handler = _content_handlers[str(selected)]

        copied = selected
        copied.parameters = selected.parameters.copy()
        encoding, response_bytes = handler.pack_bytes(response_dict)
        copied.parameters['charset'] = encoding
        self.set_header('Content-Type', str(copied))
        self.write(response_bytes)
