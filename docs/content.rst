.. py:currentmodule:: glinda.content

Content Handling
================
The ``glinda.content`` module includes functions and classes that make
content negotiation in Tornado easier to extend.  Tornado's web framework
includes :meth:`~tornado.web.RequestHandler.get_body_argument` which handles
a handful of body encodings.  It is difficult to add new content type handlers
in the current framework.  Instead of adding all of the logic into the
:class:`~tornado.web.RequestHandler`, ``glinda.content`` maintains a mapping
from content type to encoder and decoder callables and exposes a mix-in that
implements content negotiation over a :class:`~tornado.web.RequestHandler`.

The :meth:`~HandlerMixin.get_request_body` method added by the
:class:`HandlerMixin` class will decode and cache the request body based on
a set of registered content types.  You register encoder and decoder functions
associated with specific content types when your application starts up and
the :class:`HandlerMixin` will call them when it decodes the request body.
Request bodies are exposed from Tornado as raw byte strings.  Calling
:func:`.register_binary_type` associates binary transcoding functions with a
specific MIME content type.

.. code-block:: python

   from glinda import content
   import msgpack

   content.register_binary_type('application/msgpack', msgpack.dumpb,
                                msgpack.loadb)

The transcoding functions are called to translate between ``dict`` and
``byte`` representations when the :mailheader:`Content-Type` header matches
the specified value.

Many HTTP payloads are text-based and the protocol includes character set
negotiation separately from the content type.  The character set of the
request body is usually indicated by the ``charset`` content parameter ala
``Content-Type: application/json; charset=utf-8``.  You can register string-
based transcoding functions with :func:`.register_text_type`.  Request body
processing will decode the byte string into a :class:`str` instance according
to the detected character set before calling text-based decoding functions.
If a character set is not included in the request headers, then an application
specified default value is used.

.. code-block:: python

   from glinda import content
   import json

   content.register_text_type('application/json', 'utf-8',
                              json.dumps, json.loads)

Binary registrations are preferred over text since they do not require the
character transcoding process.

Functions
---------
.. autofunction:: register_binary_type

.. autofunction:: register_text_type

.. autofunction:: clear_handlers

Classes
-------
.. autoclass:: HandlerMixin
   :members:
