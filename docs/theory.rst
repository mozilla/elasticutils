======================
 ElasticSearch theory
======================

Indexes and types
=================

ElasticSearch stores documents in an index allowing you to search
them. The index is a container for documents. You can have multiple
indexes in your cluster of ElasticSearch nodes.

Documents are typed. A type has a list of fields that are in the
documents of that type. ElasticUtils calls this a "mapping type" or a
"doc type" since the word "type" is somewhat ambiguous depending on
the context.


.. seealso::

   http://www.elasticsearch.org/guide/reference/glossary/#index
     ElasticSearch explanation of indexes

   http://www.elasticsearch.org/guide/reference/glossary/#mapping
     ElasticSearch explanation of mappings

   http://www.elasticsearch.org/guide/reference/glossary/#type
     ElasticSearch explanation of types


Queries vs. filters
===================

A search can contain queries and filters. The two things are very
different.

A **filter** determines whether a document is in the results set or
not. It doesn't affect scores.  If you do a term filter on whether
field `foo` has value `bar`, then the result set ONLY has documents
where `foo` has value `bar`.  Filters are fast and filter results are
cached in ElasticSearch when appropriate. Use filters when you can.

A **query** affects the score for a document. If you do a term query
on whether field `foo` has value `bar`, then the result set will score
documents where the query holds true higher than documents where the
query does not hold true. Queries are slower than filters and query
results are not cached in ElasticSearch.

The other place where this affects things is when you specify
facets. See :ref:`queries-chapter-facets-section` for details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch Filters and Caching notes
