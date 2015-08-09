.. py:currentmodule:: glinda.testing.services

Testing Utilities
=================
:py:mod:`glinda.testing.services` contains four classes that make
testing Tornado applications that make HTTP requests against other
services much easier.  The problem that I set out to solve was how
to exercise as much of the HTTP stack as possible without running
an external service in it's entirety.  What I came up with is the
:class:`ServiceLayer` class.  It is responsible for creating and
maintaining a :class:`~tornado.web.Application` instance that you
configure to look and act like the external services that the
application under test interacts with during the test run.

The expected usage pattern is as follows:

1. create an instance of :class:`ServiceLayer` in ``setUp`` and save
   it in an instance variable for future use
2. add services by calling :class:`ServiceLayer.get_service` for each
   service that your application uses.
3. configure your application to connect to the fake services.  The
   :meth:`Service.url_for` method can be used to build URLs or you
   can retrieve the IP address and port from the :data:`Service.host`
   attribute.
4. add requests and responses using :meth:`Service.add_response` to
   configure each specific test before calling your application
   endpoints

There is a fully functional example below in `Example Test`_

Classes
-------

ServiceLayer
~~~~~~~~~~~~
.. autoclass:: ServiceLayer
   :members:

Service
~~~~~~~
.. autoclass:: Service
   :members:

Request
~~~~~~~
.. autoclass:: Request
   :members:

Response
~~~~~~~~
.. autoclass:: Response
   :members:

Example Test
------------
.. literalinclude:: ../examples/testing.py
