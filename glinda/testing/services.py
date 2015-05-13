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

    def add_endpoint(self, service, resource):
        """
        Register an endpoint that a service provides.

        :param str service: name that you refer to this service by
        :param str resource: path to install into this service

        """
        pass

    def get_service_url(self, service, *path, **query):
        """
        Get a URL to a resource within a service.

        :param str service: name that you assigned to the service
        :param path: optional path to the request
        :param query: optional query parameters to attach to the URL
        :return: the absolute URL that identifies the specified request

        """
        pass

    def add_response(self, service, request, response):
        """
        Register a response for a service.

        :param str service: name that you assigned to the service
        :param .Request request: request that will trigger the response
        :param .Response response: value to be returned from the service

        """
        pass


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
