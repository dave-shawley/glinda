glinda
======

|ReadTheDocs| |Travis| |CodeClimate|

Glinda is a companion library for `tornado`_.  It is an attempt to make your
time with the framework less painful.  In fact, I want to make it downright
enjoyable.  I started down the path of developing HTTP endpoints in Tornado
and needing to test them.  The `tornado.testing`_ package is handy for
testing endpoints in isolation.  But what do you do when you have a HTTP
service that is calling other HTTP services asynchronously.  It turns out
that testing that is not as easy as it should be.  That is the first thing
that I tackled and it is the first thing that this library is going to
offer -- *a way to test non-trivial services*.

Once you can test your application, the next step is to write a well-behaved
application that fits into the WWW nicely.  Tornado does a pretty nice job
of handling the nitty gritty HTTP details (e.g., CTE, transfer encodings).
It doesn't provide a clean way to handle representations transparently so
I decided to add that into this library as well.

Content Handling
----------------
Tornado has some internal content decoding accessible by calling the
``get_body_arguments`` method of ``tornado.web.RequestHandler``.  It will
decode basic form data, ``application/x-www-form-urlencoded`` and
``multipart/form-data`` specifically.  Anything else is left up to you.
``glinda`` exposes a content handling mix-in that imbues a standard
``RequestHandler`` with a property that is the decoded request body and
a new method to encode a response.  Here's what it looks like:

.. code-block:: python

   class MyHandler(glinda.content.HandlerMixin, web.RequestHandler):
       def post(self, *args, **kwargs):
           body_argument = self.request_body['arg']
           # do stuff
           self.send_response(response_dict)
           self.finish()

   if __name__ == '__main__':
       glinda.content.register_text_type('application/json',
                                         default_charset='utf-8',
                                         dumper=json.dumps, loader=json.loads)
       glinda.content.register_binary_type('application/msgpack',
                                           msgpack.dumpb, msgpack.loadb)

When the client sends a post with a content type of ``application/json``, it
will decode the binary body to a string according to the HTTP headers and
call ``json.loads`` to decode the body when you reference the ``request_body``
property.  Failures are handled by raising a ``HTTPError(400)`` so you don't
have to worry about handling malformed messages.  The ``send_response``
method will take care of figuring out the appropriate content type based on
any included ``Accept`` headers.  All that you have to do is install
encoding and decoding handlers for expected content types.

The ``glinda.content`` package implements content handling as described in
`RFC7231`_.  Specifically, it decodes request bodies as described in
`section 3.1`_ and proactive content negotiation as described in sections
`3.4.1`_ and `5.3`_.

Testing
-------
Here's an example of testing a Tornado endpoint that asynchronously calls
another service.  In this case, the application interacts with  with the
``/add`` endpoint of some other service.  Testing in isolation can be tricky
without having to have a copy of the service running.  You could mock out
the ``AsyncHTTPClient`` and return fake futures and what not but that has
the nasty side-effect of hiding defects around how content type or headers
are handled -- no HTTP requests means that you have untested assumptions.

The following snippet tests the application under test using the
``ServiceLayer`` abstraction that ``glinda.testing`` provides.

.. code-block:: python

   from tornado import testing
   from glinda.testing import services


   class MyServiceTests(testing.AsyncHTTPTestCase):

      def setUp(self):
         service_layer = services.ServiceLayer()
         self.service = service_layer['adder']
         # TODO configured your application here using
         # self.service.url_for('/add') or self.service.host
         super(MyServiceTests, self).setUp()

      def get_app(self):
         return MyApplication()

      def test_that_my_service_calls_other_service(self):
         self.service.add_response(
            services.Request('POST', '/add'),
            services.Response(200, body='{"result": 10}'))
         self.fetch(self.get_url('/do-stuff'), method='GET')

         recorded = self.service.get_request('/add')
         self.assertEqual(recorded.method, 'POST')
         self.assertEqual(recorded.body, '[1,2,3,4]')
         self.assertEqual(recorded.headers['Content-Type'], 'application/json')

The application under test is linked in by implementing the standard
``tornado.testing.AsyncHTTPTestCase.get_app`` method.  Then you add in
a ``glinda.testing.services.ServiceLayer`` object and configure it to look
like the services that you depend on by adding endpoints and then configuring
your application to point at the service layer.  When you invoke the
application under test using ``self.fetch(...)``, it will send HTTP requests
through the Tornado stack (using the testing ``ioloop``) to the service layer
which will respond appropriately.  The beauty is that the entire HTTP stack is
exercised locally so that you can easily test edge cases such as correct
handling of status codes, custom headers, or malformed bodies without
resorting to deep mocking.

Where?
------
+---------------+-------------------------------------------------+
| Source        | https://github.com/dave-shawley/glinda          |
+---------------+-------------------------------------------------+
| Status        | https://travis-ci.org/dave-shawley/glinda       |
+---------------+-------------------------------------------------+
| Download      | https://pypi.python.org/pypi/glinda             |
+---------------+-------------------------------------------------+
| Documentation | http://glinda.readthedocs.org/en/latest         |
+---------------+-------------------------------------------------+
| Issues        | https://github.com/dave-shawley/glinda          |
+---------------+-------------------------------------------------+

.. _tornado: http://tornadoweb.org/
.. _tornado.testing: http://www.tornadoweb.org/en/latest/testing.html
.. _RFC7231: http://tools.ietf.org/html/rfc7231
.. _section 3.1: http://tools.ietf.org/html/rfc7231#section-3.1
.. _3.4.1: http://tools.ietf.org/html/rfc7231#section-3.4.1
.. _5.3: http://tools.ietf.org/html/rfc7231#section-5.3

.. |ReadTheDocs| image:: https://readthedocs.org/projects/glinda/badge/
   :target: https://glinda.readthedocs.org/
.. |Travis| image:: https://travis-ci.org/dave-shawley/glinda.svg
   :target: https://travis-ci.org/dave-shawley/glinda
.. |CodeClimate| image:: https://codeclimate.com/github/dave-shawley/glinda/badges/gpa.svg
   :target: https://codeclimate.com/github/dave-shawley/glinda
