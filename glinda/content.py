import logging

from ietfparse import algorithms, datastructures, errors, headers
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
        assert self.bytes_to_dict or self.string_to_dict
        encoding = encoding or self.default_encoding
        LOGGER.debug('%r decoding %d bytes with encoding of %s',
                     self, len(obj_bytes), encoding)
        if self.bytes_to_dict:
            return escape.recursive_unicode(self.bytes_to_dict(obj_bytes))
        return self.string_to_dict(obj_bytes.decode(encoding))

    def pack_bytes(self, obj_dict, encoding=None):
        """Pack a dictionary into a byte stream."""
        assert self.dict_to_bytes or self.dict_to_string
        encoding = encoding or self.default_encoding or 'utf-8'
        LOGGER.debug('%r encoding dict with encoding %s', self, encoding)
        if self.dict_to_bytes:
            return None, self.dict_to_bytes(obj_dict)
        try:
            return encoding, self.dict_to_string(obj_dict).encode(encoding)
        except LookupError as error:
            raise web.HTTPError(
                406, 'failed to encode result %r', error,
                reason='target charset {0} not found'.format(encoding))
        except UnicodeEncodeError as error:
            LOGGER.warning('failed to encode text as %s - %s, trying utf-8',
                           encoding, str(error))
            return 'utf-8', self.dict_to_string(obj_dict).encode('utf-8')

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
    content_type.parameters.clear()
    key = str(content_type)
    _content_types[key] = content_type

    handler = _content_handlers.setdefault(key, _ContentHandler(key))
    handler.dict_to_string = dumper
    handler.string_to_dict = loader
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
    content_type.parameters.clear()
    key = str(content_type)
    _content_types[key] = content_type

    handler = _content_handlers.setdefault(key, _ContentHandler(key))
    handler.dict_to_bytes = dumper
    handler.bytes_to_dict = loader


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
    def registered_content_types(self):
        """Yields the currently registered content types in some order."""
        for content_type in _content_types.keys():
            yield content_type

    def get_request_body(self):
        """
        Decodes the request body and returns it.

        :return: the decoded request body as a :class:`dict` instance.
        :raises: :class:`tornado.web.HTTPError` if the body cannot be
            decoded (415) or if decoding fails (400)

        """
        if self._request_body is None:
            content_type_str = self.request.headers.get(
                'Content-Type', 'application/octet-stream')
            LOGGER.debug('decoding request body of type %s', content_type_str)
            content_type = headers.parse_content_type(content_type_str)
            try:
                selected, requested = algorithms.select_content_type(
                    [content_type], _content_types.values())
            except errors.NoMatch:
                raise web.HTTPError(
                    415, 'cannot decoded content type %s', content_type_str,
                    reason='Unexpected content type')
            handler = _content_handlers[str(selected)]
            try:
                self._request_body = handler.unpack_bytes(
                    self.request.body,
                    encoding=content_type.parameters.get('charset'),
                )
            except ValueError as error:
                raise web.HTTPError(
                    400, 'failed to decode content body - %r', error,
                    reason='Content body decode failure')
        return self._request_body

    def send_response(self, response_dict):
        """
        Encode a response according to the request.

        :param dict response_dict: the response to send

        :raises: :class:`tornado.web.HTTPError` if no acceptable content
            type exists

        This method will encode `response_dict` using the most appropriate
        encoder based on the :mailheader:`Accept` request header and the
        available encoders.  The result is written to the client by calling
        ``self.write`` after setting the response content type using
        ``self.set_header``.

        """
        accept = headers.parse_http_accept_header(
            self.request.headers.get('Accept', '*/*'))
        try:
            selected, _ = algorithms.select_content_type(
                accept, _content_types.values())
        except errors.NoMatch:
            raise web.HTTPError(406,
                                'no acceptable content type for %s in %r',
                                accept, _content_types.values(),
                                reason='Content Type Not Acceptable')

        LOGGER.debug('selected %s as outgoing content type', selected)
        handler = _content_handlers[str(selected)]

        accept = self.request.headers.get('Accept-Charset', '*')
        charsets = headers.parse_accept_charset(accept)
        charset = charsets[0] if charsets[0] != '*' else None
        LOGGER.debug('encoding response body using %r with encoding %s',
                     handler, charset)
        encoding, response_bytes = handler.pack_bytes(response_dict,
                                                      encoding=charset)

        if encoding:  # don't overwrite the value in _content_types
            copied = datastructures.ContentType(selected.content_type,
                                                selected.content_subtype,
                                                selected.parameters)
            copied.parameters['charset'] = encoding
            selected = copied
        self.set_header('Content-Type', str(selected))
        self.write(response_bytes)
