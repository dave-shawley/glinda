glinda
======

|Version| |Downloads| |Status| |License|

Wait... Why? What??
-------------------
Glinda is a companion library for `tornado`_.  It is an attempt to make your
time with the framework less painful.  In fact, I want to make it downright
enjoyable.  I started down the path of developing HTTP endpoints in Tornado
and needing to test them.  The `tornado.testing`_ package is handy for
testing endpoints in isolation.  But what do you do when you have a HTTP
service that is calling other HTTP services asynchronously.  It turns out
that testing that is not as easy as it should be.  That is the first thing
that I tackled and it is the first thing that this library is going to
offer -- *a way to test non-trivial services*.

Here's an example.  Assume that you have a Tornado application that interacts
with the ``/add`` endpoint of some other service.  Testing in isolation can
be tricky without having to have a copy of the service running.  The other
option is to deeply mock things which has a nasty side-effect of hiding
defects around how content type or headers are handled -- no HTTP requests
means that you have untested assumptions.  Instead, consider the following
example.

.. code-block:: python

   from tornado import testing
   from glinda.testing import services


   class MyServiceTests(testing.AsyncHTTPTestCase):

      def setUp(self):
         self.service_layer = services.ServiceLayer()
         self.service_layer.add_endpoint('adder', '/add')
         # TODO configured your application here using
         # self.service_layer.get_url_for('adder', '/add')
         super(MyServiceTests, self).setUp()

      def get_app(self):
         return MyApplication()

      @testing.gen_test
      def test_that_my_service_calls_other_service(self):
         self.service_layer.add_response(
            'adder',
            services.Request('POST', '/add'),
            services.Response(200, body='{"result": 10}'))
         yield self.http_client.fetch(self.get_url('/do-stuff'), method='GET')

         recorded = self.service_layer.get_request(
            'adder', services.Request('POST', '/add'))
         self.assertEqual(recorded.body, '[1,2,3,4]')
         self.assertEqual(recorded.headers['Content-Type'], 'application/json')

The application under test is linked in by implementing the standard
``tornado.testing.AsyncHTTPTestCase.get_app`` method.  Then you add in
a ``glinda.testing.services.ServiceLayer`` object and configure it to look
like the services that you depend on by adding endpoints and then configuring
your application to point at the service layer.  When you invoke the
application under test using ``yield self.http_client.fetch(...)``, it will
send HTTP requests through the Tornado stack (using the testing ``ioloop``)
to the service layer which will respond appropriately.  The beauty is that
the entire HTTP stack is exercised locally so that you can easily test edge
cases such as correct handling of status codes, custom headers, or malformed
bodies without resorting to deep mocking.

That is a sample of what this library aims to provide.  It starts with being
able to develop Tornado applications and test them quickly, easily, and as
completely as possible.  Let's do some of that, shall we?

Ok... Where?
------------

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

.. |Version| image:: https://pypip.in/version/glinda/badge.svg
   :target: https://pypi.python.org/pypi/glinda
.. |Downloads| image:: https://pypip.in/d/glinda/badge.svg
   :target: https://pypi.python.org/pypi/glinda
.. |Status| image:: https://travis-ci.org/dave-shawley/glinda.svg
   :target: https://travis-ci.org/dave-shawley/glinda
.. |License| image:: https://pypip.in/license/glinda/badge.svg
   :target: https://github.com/dave-shawley/glinda/blob/master/LICENSE
