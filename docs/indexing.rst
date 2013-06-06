==========
 Indexing
==========

.. contents::
   :local:


Overview
========

ElasticUtils is primarily an API for searching. However, before you
can search, you need to create an index and index your documents.

This chapter covers the indexing side of things. It does so
lightly---for more details, read through the `pyelasticsearch
documentation <http://pyelasticsearch.readthedocs.org/en/latest/>`_
and the `Elasticsearch guide <http://www.elasticsearch.org/guide/>`_.


Getting an ElasticSearch object
===============================

ElasticUtils uses `pyelasticsearch` which comes with a handy
`ElasticSearch` object. This lets you:

* create indexes
* create mappings
* apply settings
* check status
* etc.

To access this, you use :py:func:`elasticutils.get_es` which creates
an `ElasticSearch` object for you.

See :py:func:`elasticutils.get_es` for more details.


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/
     pyelasticsearch ElasticSearch documentation.


Indexes
=======

An `index` is a collection of documents.

Before you do anything, you need to have an index. You can create one
with `.create_index()`.

For example:

.. code-block:: python

    es = get_es()
    es.create_index('blog-index')


You can pass in settings, too. For example, you can set the refresh
interval when creating the index:

.. code-block:: python

    es.create_index('blog-index', settings={'refresh_interval': '5s'})


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.create_index
     pyelasticsearch create_index API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-create-index/
     Elasticsearch create_index API documentation


.. _indexing-types-and-mappings:

Types and Mappings
==================

A `type` is a set of fields. A document is of a given type if it has
those fields. Whenever you index a document, you specify which type
the document is. This is sometimes called a "doctype", "document type"
or "doc type".

A `mapping` is the definition of fields and how they should be indexed
for a type. In ElasticUtils, we call a document type that has a
defined mapping a "mapping type" mostly as a shorthand for "document
type with a defined mapping" because that's a mouthful.

Elasticsearch can infer mappings to some degree, but you get a lot
more value by specifying mappings explicitly.

To define a mapping, you use `.put_mapping()`.

For example:

.. code-block:: python

    es = get_es()
    es.put_mapping('blog-index', 'blog-entry-type', {
        'id': {'type': 'integer'},
        'title': {'type': 'string'},
        'content': {'type': 'string'},
        'tags': {'type': 'string'},
        'created': {'type': 'date'}
        })


You can also define mappings when you create the index:

.. code-block:: python

    es = get_es()
    es.create_index('blog-index', settings={
        'mappings': {
            'blog-entry-type': {
                'id': {'type': 'integer'},
                'title': {'type': 'string'},
                'content': {'type': 'string'},
                'tags': {'type': 'string'},
                'created': {'type': 'date'}
            }}})


.. Note::

   If there's a possibility of a race condition between creating the
   index and defining the mapping and some document getting indexed,
   then it's good to create the index and define the mappings at the
   same time.


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.put_mapping
     pyelasticsearch put_mapping API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-put-mapping/
     Elasticsearch put_mapping API documentation

   http://www.elasticsearch.org/guide/reference/mapping/
     Elasticsearch mapping documentation


Indexing documents
==================

Use `.index()` to index a document.

For example:

.. code-block:: python

    es = get_es()

    entry = {'id': 1,
        'title': 'First post!',
        'content': '<p>First post!</p>',
        'tags': ['status', 'blog'],
        'created': '20130423T16:50:22'
        }

    es.index('blog-index', 'blog-entry-type', entry, 1)


If you're indexing a bunch of documents at the same time, you should
use `.bulk_index()`.

For example:

.. code-block:: python

    es = get_es()

    entries = { ... }

    es.bulk_index('blog-index', 'blog-entry-type', entries, id_field='id')


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.index
     pyelasticsearch index API documentation

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.bulk_index
     pyelasticsearch bulk_index API documentation

   http://www.elasticsearch.org/guide/reference/api/index\_/
     Elasticsearch index API documentation

   http://www.elasticsearch.org/guide/reference/api/bulk/
     Elasticsearch bulk index API documentation


Deleting documents
==================

You can delete documents with `.delete()`.

For example:

.. code-block:: python

    es = get_es()

    es.delete('blog-index', 'blog-entry-type', 1)


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.delete
     pyelasticsearch delete API documentation

   http://www.elasticsearch.org/guide/reference/api/delete/
     Elasticsearch delete API documentation


Refreshing
==========

After you index documents, they're not available for searches until
after the index is refreshed. By default, the index refreshes every
second. If you need the documents to show up in searches before that,
call `.refresh()`.

For example:

.. code-block:: python

    es = get_es()

    es.refresh('blog-index')


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.refresh
     pyelasticsearch refresh API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-refresh/
     Elasticsearch refresh API documentation


Delete indexes
==============

You can delete indexes with `.delete_index()`.

For example:

.. code-block:: python

    es = get_es()

    es.delete_index('blog-index')


.. seealso::

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.delete_index
     pyelasticsearch delete_index API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-delete-index/
     Elasticsearch delete index API documentation


Doing all of this with MappingTypes and Indexables
==================================================

If you're using MappingTypes, then you can do much of the above using
methods and classmethods on :py:class:`MappingType` and
:py:class:`Indexable` classes. See :ref:`mapping-type-chapter` for
more details.
