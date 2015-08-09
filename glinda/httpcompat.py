"""
HTTP compatibility shim.

This is a poor man's six without the headache of another dependency
that might conflict.

"""
try:
    from urllib.parse import parse_qs, quote, urlencode, urlsplit, urlunsplit
except ImportError:  # pragma: no cover
    from urllib import quote, urlencode
    from urlparse import parse_qs, urlsplit, urlunsplit

__all__ = ('parse_qs', 'quote', 'urlencode', 'urlsplit', 'urlunsplit')
