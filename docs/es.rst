=============
Getting an ES
=============

ElasticUtils uses `pyes` which comes with a handy `ES` object. This
lets you work with ElasticSearch outside of what ElasticUtils can do.

To access this, you use `get_es()` which builds an `ES`.

.. autofunction:: elasticutils.get_es


.. Warning::

   ElasticUtils works with ``pyes`` 0.15 and 0.16. The API for later
   versions of pyes has changed too much and won't work with
   ElasticUtils. We're planning to switch to something different in
   the future.
