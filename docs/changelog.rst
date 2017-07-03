Changelog
---------

* `Next Release`_

  - Modify content negotiation to 406 when asked for an unknown character set
  - Add :attr:`glinda.content.HandlerMixin.registered_content_types`
  - Add directory of examples
  - Remove support for tornado newer than 4.5.  *This is tempory due to changes
    in the Tornado API*.

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

.. _Next Release: https://github.com/dave-shawley/glinda/compare/0.0.3...master
.. _0.0.3: https://github.com/dave-shawley/glinda/compare/0.0.2...0.0.3
.. _0.0.2: https://github.com/dave-shawley/glinda/compare/0.0.1...0.0.2
.. _0.0.1: https://github.com/dave-shawley/glinda/compare/0.0.0...0.0.1
