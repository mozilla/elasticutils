==
ES
==

`pyes` comes with a handy `ES` object. `elasticutils` has a `get_es()`
function which builds an `ES`.

.. autofunction:: elasticutils.get_es


.. Warning::

   ElasticUtils works best with ``pyes`` 0.15 and 0.16. The API for
   later versions has changed too drastically. While we'd welcome
   compatibility patches, we feel a better approach would be to remove
   our dependency on ``pyes``.
