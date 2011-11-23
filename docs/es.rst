==
ES
==

`pyes` comes with a handy `ES` object.  In order to make sure we're using the
same `ES` object, `elasticutils` comes with `get_es()` which will use a single
`ES` in a single thread.

.. Note::

    If you don't want to use a shared `ES` (cached thread-local), create your
    own `pyes.ES`. This is useful if you want to create an `ES` that has
    different settings (e.g. a longer timeout).
