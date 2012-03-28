==
ES
==

`pyes` comes with a handy `ES` object. `elasticutils` has a `get_es()`
function which builds an `ES` and if it's generic, will cache it
thread-local.

.. autofunction:: elasticutils.get_es


.. Note::

   `get_es()` only caches the `ES` if you don't pass in any override
   arguments. If you pass in override arguments, it doesn't cache it,
   but instead creates a new one.

.. Warning::

   ElasticUtils works best with ``pyes`` 0.15. The API for later
   versions has changed too drastically. While we'd welcome
   compatibility patches, we feel a better approach would be to remove
   our dependency on ``pyes``.
