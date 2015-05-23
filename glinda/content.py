import logging

from ietfparse import algorithms, headers, errors
from tornado import web, escape


LOGGER = logging.getLogger(__name__)


class _ContentHandler(object):
    """
    Translate between dictionaries and bytes.

    Instances of this class translate between request and response
    objects represented as dictionaries and the byte strings that
    Tornado wants.  The translation is implemented using callable
    hooks that handle bytes and/or strings.  If a byte-related hook
    is available, then it is used; otherwise, the string-related hook
    is used and the translation between bytes and strings is handled
    inside of the method.

    """

    def __init__(self, content_type):
        super(_ContentHandler, self).__init__()
        self.content_type = content_type
        self.dict_to_string = None
        self.string_to_dict = None
        self.dict_to_bytes = None
        self.bytes_to_dict = None
        self.default_encoding = None

    def unpack_bytes(self, obj_bytes, encoding=None):
        """Unpack a byte stream into a dictionary."""
        encoding = encoding or self.default_encoding
        LOGGER.debug('%r decoding %d bytes with encoding of %s',
                     self, len(obj_bytes), encoding)
        if self.bytes_to_dict:
            return escape.recursive_unicode(self.bytes_to_dict(obj_bytes))
        return self.string_to_dict(obj_bytes.decode(encoding))

    def pack_bytes(self, obj_dict, encoding=None):
        """Pack a dictionary into a byte stream."""
        encoding = encoding or self.default_encoding
        LOGGER.debug('%r encoding dict with encoding %s', self, encoding)
        if self.dict_to_bytes:
            return None, self.dict_to_bytes(obj_dict)
        return encoding, self.dict_to_string(obj_dict).encode(encoding)

    def __repr__(self):
        return '<{}.{} for {} unpacks {}, packs {}>'.format(
            self.__module__, self.__class__.__name__,
            self.content_type,
            'binary' if self.bytes_to_dict else 'str',
            'binary' if self.dict_to_bytes else 'str',
        )


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

    handler = _content_handlers.setdefault(key, _ContentHandler(key))
    handler.dict_to_string = dumper or handler.dict_to_string
    handler.string_to_dict = loader or handler.string_to_dict
    handler.default_encoding = default_encoding or handler.default_encoding


def register_binary_type(content_type, dumper, loader):
    """
    Register handling for a binary content type.

    :param str content_type: content type to register the hooks for
    :param dumper: called to decode bytes into a dictionary.
        Calling convention: ``dumper(obj_dict) -> bytes``.
    :param loader: called to encode a dictionary into a byte string.
        Calling convention: ``loader(obj_bytes) -> dict``

    """
    content_type = headers.parse_content_type(content_type)
    key = str(content_type)
    _content_types[key] = content_type

    handler = _content_handlers.setdefault(key, _ContentHandler(key))
    handler.dict_to_bytes = dumper or handler.dict_to_bytes
    handler.bytes_to_dict = loader or handler.bytes_to_dict


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
            LOGGER.debug('decoding request body of type %s', content_type_str)
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
        accept = headers.parse_http_accept_header(
            self.request.headers.get('Accept', '*/*'))
        selected, _ = algorithms.select_content_type(
            accept, _content_types.values())
        handler = _content_handlers[str(selected)]

        LOGGER.debug('encoding response body using %r', handler)
        encoding, response_bytes = handler.pack_bytes(response_dict)

        copied = selected
        copied.parameters = selected.parameters.copy()
        if encoding:
            copied.parameters['charset'] = encoding
        self.set_header('Content-Type', str(copied))
        self.write(response_bytes)
