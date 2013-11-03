=========================
 More like this: ``MLT``
=========================

ElasticUtils exposes Elasticsearch More Like This API with the `MLT`
class.

For example::

    mlt = MLT(2034, index='addon_index', doctype='addon')


This creates an `MLT` that will return documents that are like
document with id 2034 of type `addon` in the `addon_index`.

You can pass it an `S` instance and the `MLT` will derive the index,
doctype, ElasticSearch object and also use the search specified by
the `S` in the body of the More Like This request. This allows you to
get documents like the one specified that also meet query and filter
criteria. For example::

    s = S().filter(product='firefox')
    mlt = MLT(2034, s=s)


See :py:class:`elasticutils.MLT` for more details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/more-like-this.html
     Elasticsearch guide on More Like This API

   http://www.elasticsearch.org/guide/reference/query-dsl/mlt-query.html
     Elasticsearch guide on the moreLikeThis query which specifies the
     additional parameters you can use.

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.Elasticsearch.mlt
     elasticsearch-py documentation for MLT
