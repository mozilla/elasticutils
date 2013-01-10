.. _es-chapter:

===============================
Getting an ElasticSearch object
===============================

ElasticUtils uses `pyelasticsearch` which comes with a handy
`ElasticSearch` object. This lets you work with ElasticSearch outside
of what ElasticUtils can do.

To access this, you use `get_es()` which builds an `ElasticSearch`
object.


.. autofunction:: elasticutils.get_es


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/
     pyelasticsearch ElasticSearch documentation.
