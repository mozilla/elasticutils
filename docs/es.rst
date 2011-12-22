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

.. warning::
  ElasticUtils works best with ``pyes`` 0.15.  The API for later versions
  has changed too drastically.   While we'd welcome compatibility patches,
  we feel a better approach would be to remove our dependency on ``pyes``.
