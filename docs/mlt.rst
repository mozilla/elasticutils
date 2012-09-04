=======================
More like this with MLT
=======================

.. contents::
   :local:


Overview
========

ElasticUtils exposes ElasticSearch More Like This API with the `MLT`
class.

For example::

    mlt = MLT(2034, index='addon_index', doctype='addon')


This creates an `MLT` that will return documents that are like
document 2034 of type `addon` in the `addon_index`.

You can specify an `S` and the `MLT` will derive the index, doctype,
ES object, and also use the search specified by the S in the body of
the More Like This request. This allows you to get documents like the
one specified that also meet query and filter criteria. For example::

    s = S().filter(product='firefox')
    mlt = MLT(2034, s=s)


You can specify which fields to use with the `fields` argument. If you
don't, then ElasticSearch will use all the fields.

You can specify additional parameters. See the `documentation on the
moreLikeThis query
<http://www.elasticsearch.org/guide/reference/query-dsl/mlt-query.html>`_.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/more-like-this.html
     ElasticSearch guide on More Like This API

   http://www.elasticsearch.org/guide/reference/query-dsl/mlt-query.html
     ElasticSearch guide on the moreLikeThis query which specifies the
     additional parameters you can use.


API
===

.. autoclass:: elasticutils.MLT
   :members:

   .. automethod:: elasticutils.MLT.__init__
