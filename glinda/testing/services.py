"""
Classes for testing applications that make asynchronous HTTP requests.

- ``ServiceLayer``: testing fixture that manages request handlers
  that your tests will interact with
- ``Service``: represents a single HTTP service that the application
  under test will interact with
- ``Request``: represents a request that the application under test
  makes.  ``Service`` instances are configured to respond to requests
  from the application using ``Request`` instances.
- ``Response``: used to configure what a ``Service`` instance will
  respond with

"""
import collections
import logging
import socket

from tornado import gen, httpserver, httputil, web

from glinda import httpcompat


class ServiceLayer(object):
    """
    Represents any number of HTTP services.

    Create an instance of this class to represent any number of HTTP
    services that your application depends on.  It attaches to the
    :class:`~tornado.ioloop.IOLoop` instance that the standard
    :class:`~tornado.testing.AsyncTestCase` supplies and manages
    the Tornado machinery necessary to glue :class:`Service` instances
    to the ioloop.  Each external service that you need to test with
    is represented by a named :class:`Service` instance.  The
    :class:`Service` instance maintains the list of programmed responses.
    The :class:`ServiceLayer` exists to make sure that the requests get to
    the appropriate handler.

    Each managed service is exposed as named :class:`.Service` instance
    that is owned by the :class:`ServiceLayer` instance.  They are created
    on-demand by calling :meth:`.get_service` with the name that you
    assign to them.  The :class:`ServiceLayer` instance implements the same
    behavior as item lookup as well (e.g., ``__getitem__``)::

        >>> from tornado.ioloop import IOLoop
        >>> services = ServiceLayer()
        >>> services['service-name'] is services.get_service('service-name')
        True

    Once you have a named service instance, you can configure it to
    respond by calling :meth:`Service.add_response` method.

        >>> from tornado import httpclient, ioloop
        >>> services = ServiceLayer()
        >>> service = services.get_service('endpoint')
        >>> service.add_response(Request('GET', '/endpoint'),
        ...                      Response(222))
        >>> def get():
        ...    client = httpclient.AsyncHTTPClient()
        ...    return client.fetch(service.url_for('endpoint'))
        >>> rsp = ioloop.IOLoop.instance().run_sync(get)
        >>> rsp.code
        222
        >>>

    Note that the ``get`` function in the example mimics the application
    under test asynchronously interacting with a service within the
    service layer.

    """

    def __init__(self):
        """Initialize the service layer."""
        super(ServiceLayer, self).__init__()
        self._application = _Application()
        self._server = httpserver.HTTPServer(self._application)
        self._services = {}

    def get_service(self, service):
        """
        Retrieve a named service, creating it if necessary.

        :param str service: name to assign to the service
        :return: a :class:`Service` instance

        This method creates the new :class:`Service` instance and
        wires it into the tornado stack listening on its own port
        number.  If the service already exists, then it is returned
        without modification.

        """
        try:
            service_instance = self._services[service]
        except KeyError:
            service_instance = Service(service, self._application.add_resource)
            self._server.add_socket(service_instance.acceptor)
            self._services[service] = service_instance
        return service_instance

    __getitem__ = get_service


class Request(object):
    """
    Matches a request from a client.

    :param str method: HTTP method to match
    :param path: optional resource path to match

    Instances of this class are used by :class:`.Service` instances to
    identify patterns that a client will request.

    """

    def __init__(self, method, *path):
        super(Request, self).__init__()
        self.method = method
        self.resource = _quote_path(*path)
        self.body = None
        self.headers = httputil.HTTPHeaders()
        self.query = {}


class Response(object):
    """
    Records a response from the server.

    :param int status: HTTP status code to return
    :param str reason: optional phrase to return on the status line
    :param bytes body: optional payload to return
    :param dict headers: optional response headers

    """

    def __init__(self, status, reason=None, body=None, headers=None):
        super(Response, self).__init__()
        self.status = status
        self.reason = reason or 'Unspecified'
        self.body = body
        self.headers = (headers or {}).copy()


class Service(object):
    """
    Represents a logical HTTP service.

    A *service* is a collection of HTTP resources that are
    available from a ephemeral port that the service sets up
    when it is created.  When the instance is create, it is
    isolated behind a unique socket (and port number).  The
    :meth:`~Service.url_for` method will construct and return
    a URL containing the ephemeral port number and host name
    so that you can easily interact with the service.

    A service is a collection of related endpoints that is
    attached to a specific port on localhost.  It is
    responsible for keeping track of the programmed responses
    and dispatching them when requests come in.  Responses are
    added to the service with :meth:`~Service.add_response`.
    They will be returned from the request handler associated
    with a resource path in the order that they are added.

    Note that you should not create :class:`Service` instances
    yourself.  If you do, they will not be wired into the
    Tornado framework appropriately.  Instead, you should
    create a :class:`ServiceLayer` instance and call
    :meth:`ServiceLayer.get_service` to create services.

    """

    def __init__(self, name, add_resource_callback):
        """
        Initialize a new service.

        :param str name: the name of this service.  This is used to
            generate the readable representation of this resource
        :param callable add_resource_callback: object to call when
            a resource is added to this service

        """
        super(Service, self).__init__()
        self.name = name
        self.logger = logging.getLogger('.'.join([
            __package__, 'Service', name]))
        self.add_resource_callback = add_resource_callback

        self.acceptor = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                      socket.IPPROTO_TCP)
        self.acceptor.setblocking(0)
        self.acceptor.bind(('127.0.0.1', 0))
        self.acceptor.listen(10)
        self.host = '%s:%d' % self.acceptor.getsockname()
        self._requests = collections.defaultdict(list)
        self._responses = collections.defaultdict(list)
        self._endpoints = set()

        self.logger.info('listening on %s', self.host)

    def add_endpoint(self, *path):
        """
        Add an endpoint without configuring a response.

        :param path: resource path

        You only need to call this method if you want to create a resource
        without configuring a response.  Otherwise, you should call
        :meth:`.add_response` which will create the resource if necessary.

        """
        self._register_endpoint(_quote_path(*path))

    def _register_endpoint(self, path):
        """
        Register an endpoint with with this service.

        :param path: quoted resource path
        """
        if path not in self._endpoints:
            self.logger.info('adding endpoint for %s', path)
            self.add_resource_callback(self, path)
            self._endpoints.add(path)

    def add_response(self, request, response):
        """
        Configure the service to respond to a specific request.

        :param .Request request: request to match against
        :param .Response response: response to return when the
            handler receives `request`

        """
        self._register_endpoint(request.resource)
        self._responses[request.method, request.resource].append(response)

    def record_request(self, request):
        """
        Record a client request to a service.

        :param tornado.httputil.HTTPRequest request:
            client request made to one of the services endpoints

        """
        self.logger.debug('processing request: method=%s path=%s',
                          request.method, request.path)
        req = Request(request.method, request.path)
        req.body = request.body
        req.headers.update(request.headers)
        for name, value_list in request.query_arguments.items():
            assert len(value_list) < 2
            req.query[name] = value_list[0].decode('utf-8')

        self._requests[request.path].append(req)

    def url_for(self, *path, **query):
        """
        Retrieve a URL that targets the service.

        :param path: list of path elements
        :param query: optional query parameters to include in the URL
        :return: the full URL that targets the address and port for
            this service and includes the specified `path` and `query`

        """
        resource = _quote_path(*path)
        query_str = httpcompat.urlencode(sorted(query.items()))
        return httpcompat.urlunsplit(('http', self.host, resource,
                                      query_str, None))

    def get_next_response(self, tornado_request):
        """
        Retrieve the next response for a request.

        :param tornado.httputil.HTTPRequest tornado_request:

        Responses are matched to the request using the request
        method and URI as a key.  If a response was registered
        for the method and URI, then it is popped and returned.
        If there is no response configured for `tornado_request`,
        then an exception is raised.

        :raises tornado.web.HTTPError:
            with a status of 456 if the service doesn't have a
            response configured for `tornado_request`

        """
        key = tornado_request.method, tornado_request.path
        try:
            response = self._responses[key].pop(0)
            self.logger.debug('returning response for %s %s: %r',
                              tornado_request.method, tornado_request.path,
                              response)
            return response
        except IndexError:
            self.logger.error(
                'failed to find response for %s %s: response keys=%r',
                tornado_request.method, tornado_request.uri,
                list(self._responses.keys()))
            raise web.HTTPError(456, 'Unexpected request - %s %s',
                                tornado_request.method, tornado_request.uri,
                                reason='Test Configuration Error')

    def get_requests_for(self, *path):
        """
        Retrieve the requests made for `path`.

        :param path: resource to retrieve requests for

        This method returns the requests made for `path` in the order
        that they were made.  It uses a generator to return value
        values so either call it in a loop or use :func:`next` to get
        the first value.

        :returns: :class:`.Request` instances made for the resource
            by way of a generator
        :raises: :class:`AssertionError` if no requests were made for
            the resource

        """
        resource = _quote_path(*path)
        if self._requests[resource]:
            for request in self._requests[resource]:
                yield request
        else:
            raise AssertionError('Expected request for {0}'.format(resource))

    def get_request(self, *path):
        """Convenience method to fetch a single request."""
        return next(self.get_requests_for(*path))

    def assert_request(self, method, *path, **query):
        """
        Assert that a specific request was made to the service.

        :param str method: the HTTP method to match
        :param path: the resource to match
        :param query: optional query parameters to match
        :raises: :class:`AssertionError` if no matching request to
            the service is found

        """
        resource = _quote_path(*path)
        for request in self.get_requests_for(resource):
            if request.method == method and request.query == query:
                return
        else:
            raise AssertionError('Expected request for {0}'.format(resource))


class _Application(web.Application):
    """
    Tornado application that implements the service abstraction.

    This application glues the :class:`Service` instances to the
    ioloop.  Most of the logic is in the :class:`Service` instances
    and the :class:`ServiceLayer` instance.  Instead of calling the
    :meth:`add_handler` method, call :meth:`add_resource` to install
    a instance of :class:`_ServiceHandler` that will interact with
    a specific service.

    """

    def __init__(self):
        # overridden to install a default handler
        super(_Application, self).__init__([web.url('/', _ErrorHandler)])

    def add_resource(self, service, resource):
        """
        Install a :class:`_ServiceHandler` instance.

        :param Service service: the service instance to install into
            the application.  The instance is passed to the initializer
            of :class:`_ServiceHandler` when the handler is created.
        :param str resource: path to mount the new resource at

        """
        handler = web.url(resource, _ServiceHandler,
                          kwargs={'service': service})
        # leave the error handler at the end
        self.default_router.rules.insert(-1, handler)


class _ErrorHandler(web.RequestHandler):
    def prepare(self):
        raise web.HTTPError(status_code=456, reason='Unexpected Request')


class _ServiceHandler(web.RequestHandler):
    """
    Individual service endpoint.

    Each endpoint is handled by an instance of this class.  It
    does little more than proxy requests between the ioloop and
    the :class:`Service` instances.

    """

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service')
        super(_ServiceHandler, self).__init__(*args, **kwargs)

    def prepare(self):
        super(_ServiceHandler, self).prepare()
        self.service.record_request(self.request)

    @gen.coroutine
    def _do_request(self, *args, **kwargs):
        response = self.service.get_next_response(self.request)
        self.set_status(response.status, response.reason)
        for name, value in response.headers.items():
            self.set_header(name, value)
        if response.body:
            self.write(response.body)
        self.finish()

    connect = _do_request
    delete = _do_request
    get = _do_request
    head = _do_request
    patch = _do_request
    post = _do_request
    put = _do_request
    trace = _do_request


def _quote_path(*path):
    path_str = '/'.join(httpcompat.quote(segment) for segment in path)
    return path_str if path_str.startswith('/') else '/' + path_str
