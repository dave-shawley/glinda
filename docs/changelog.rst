Changelog
---------

* `1.0.1`_ (27 Jun 2019)

  - Fix errant usage of :class:`tornado.web.ErrorHandler`

* `1.0.0`_ (22 Apr 2019)

  - Adjust supported Python versions

    - Add support for 3.5, 3.6, & 3.7
    - Drop support for 3.3, & 3.4

  - Adjust supported Tornado versions

    - Add support for 4.5, 5, and 6
    - Drop support for 3-4.5

* `0.1.0`_ (3 Jul 2017)

  - Modify content negotiation to 406 when asked for an unknown character set
  - Add :attr:`glinda.content.HandlerMixin.registered_content_types`
  - Add directory of examples
  - Remove support for tornado newer than 4.5.  *This is tempory due to changes
    in the Tornado API*.
  - Change Application.add_resource so that it inserts handlers before the
    default error handler instead of after.

* `0.0.3`_ (30 May 2015)

  - Add :func:`glinda.content.clear_handlers`
  - Add :func:`glinda.content.register_binary_type`
  - Add :func:`glinda.content.register_text_type`
  - Add :class:`glinda.content.HandlerMixin`

* `0.0.2`_ (29 May 2015)

  - Make testing layer actually return the headers and bodies that
    are programmatically added via ``glinda.testing.services.Response``.

* `0.0.1`_ (21 May 2015)

  - Add :class:`glinda.testing.services.Service`
  - Add :class:`glinda.testing.services.ServiceLayer`
  - Add :class:`glinda.testing.services.Request`
  - Add :class:`glinda.testing.services.Response`

.. _Next Release: https://github.com/dave-shawley/glinda/compare/1.0.1...master
.. _1.0.1: https://github.com/dave-shawley/glinda/compare/1.0.0...1.0.1
.. _1.0.0: https://github.com/dave-shawley/glinda/compare/0.1.0...1.0.0
.. _0.1.0: https://github.com/dave-shawley/glinda/compare/0.0.3...0.1.0
.. _0.0.3: https://github.com/dave-shawley/glinda/compare/0.0.2...0.0.3
.. _0.0.2: https://github.com/dave-shawley/glinda/compare/0.0.1...0.0.2
.. _0.0.1: https://github.com/dave-shawley/glinda/compare/0.0.0...0.0.1
