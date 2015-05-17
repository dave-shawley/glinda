import collections
import socket

from tornado import gen, httpserver, web

from glinda import httpcompat


class ServiceLayer(object):
    """
    Represents any number of HTTP services.

    Create an instance of this class to represent any number of HTTP
    services that your application depends on.  It attaches to the
    :class:`~tornado.ioloop.IOLoop` instance that the standard
    :class:`~tornado.testing.AsyncTestCase` supplies and responds to
    requests that the application under test makes.

    Create *endpoints* in the service layer by calling the
    :meth:`.add_endpoint` method.  This establishes the different
    HTTP resources that you interact with.  Each HTTP service is
    isolated by listening on different ephemeral ports and routing
    requests to an application that implements host and port based
    virtual hosting.  You can access the URLs for the individual
    services with the :meth:`.get_service_url` method.  It returns an
    absolute URL that targets the internally managed service.

    You control the responses that each service will respond with by
    programming it with :meth:`.add_response` for each expected request.
    The response is matched to the incoming request using the HTTP method
    and resource that the service interacts with.

    """

    def __init__(self):
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

    Instances of this class are used by :class:`.ServiceLayer` to
    identify patterns that a client will request.

    """

    def __init__(self, method, *path):
        super(Request, self).__init__()
        self.method = method
        self.resource = '/'.join(httpcompat.quote(segment) for segment in path)
        if not self.resource.startswith('/'):
            self.resource = '/' + self.resource


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

    A service is a collection of related endpoints that is
    attached to a specific port on localhost.  It is
    responsible for keeping track of the programmed responses
    and dispatching them when requests come in.

    """

    def __init__(self, name, add_resource_callback):
        super(Service, self).__init__()
        self.name = name
        self.add_resource_callback = add_resource_callback

        self.acceptor = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                      socket.IPPROTO_TCP)
        self.acceptor.setblocking(0)
        self.acceptor.bind(('127.0.0.1', 0))
        self.acceptor.listen(10)
        self.host = '%s:%d' % self.acceptor.getsockname()
        self._responses = collections.defaultdict(list)
        self._endpoints = set()

    def add_endpoint(self, *path):
        url = '/'.join(httpcompat.quote(segment) for segment in path)
        if not url.startswith('/'):
            url = '/' + url
        if url not in self._endpoints:
            self.add_resource_callback(self, url)
            self._endpoints.add(url)

    def add_response(self, request, response):
        """
        Configure the service to respond to a specific request.

        :param .Request request:
        :param .Response response:

        """
        self.add_endpoint(request.resource)
        self._responses[request.method, request.resource].append(response)

    def url_for(self, *path, **query):
        resource = '/'.join(httpcompat.quote(segment) for segment in path)
        query_str = httpcompat.urlencode(sorted(query.items()))
        return httpcompat.urlunsplit(('http', self.host, resource,
                                      query_str, None))

    def get_next_response(self, tornado_request):
        """
        Retrieve the next response for a request.

        :param tornado.web.httpserver.HTTPRequest:

        """
        return self._responses[tornado_request.method, tornado_request.uri].pop(0)


class _Application(web.Application):
    """
    Tornado application that implements the service abstraction.

    This application glues the :class:`_Service` instances to the
    ioloop.  Most of the logic is in the :class:`_Service` instances
    and the :class:`ServiceLayer` instance.

    """

    def add_resource(self, service, resource):
        handler = web.url(resource, _ServiceHandler,
                          kwargs={'service': service})
        if self.handlers:
            self.handlers[-1][1].append(handler)
        else:
            self.add_handlers('.*', [handler])


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

    @gen.coroutine
    def _do_request(self, *args, **kwargs):
        try:
            response = self.service.get_next_response(self.request)
        except IndexError:
            raise web.HTTPError(405)

        self.set_status(response.status, response.reason)

    connect = _do_request
    delete = _do_request
    get = _do_request
    head = _do_request
    patch = _do_request
    post = _do_request
    put = _do_request
    trace = _do_request
