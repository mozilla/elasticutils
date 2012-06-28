=============
Getting an ES
=============

ElasticUtils uses `pyes` which comes with a handy `ES` object. This
lets you work with ElasticSearch outside of what ElasticUtils can do.

To access this, you use `get_es()` which builds an `ES`.

.. autofunction:: elasticutils.get_es


.. Warning::

   ElasticUtils works best with ``pyes`` 0.15 and 0.16. The API for
   later versions has changed too drastically. While we'd welcome
   compatibility patches, we feel a better approach would be to remove
   our dependency on ``pyes``.
