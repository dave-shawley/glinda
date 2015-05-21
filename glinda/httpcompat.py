"""
HTTP compatibility shim.

This is a poor man's six without the headache of another dependency
that might conflict.

"""
try:
    from urllib.parse import quote, urlencode, urlsplit, urlunsplit
except ImportError:  # pragma: no cover
    from urllib import quote, urlencode
    from urlparse import urlsplit, urlunsplit

__all__ = ('quote', 'urlencode', 'urlsplit', 'urlunsplit')
