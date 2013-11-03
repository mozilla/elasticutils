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
lightly---for more details, read through the `elasticsearch-py
documentation <http://elasticsearch-py.readthedocs.org/en/latest/>`_
and the `Elasticsearch guide <http://www.elasticsearch.org/guide/>`_.


Getting an Elasticsearch object
===============================

ElasticUtils uses `elasticsearch-py` which comes with a handy
`Elasticsearch` object. This lets you:

* create indexes
* create mappings
* apply settings
* check status
* etc.

To access this, you use :py:func:`elasticutils.get_es` which creates
an `Elasticsearch` object for you.

See :py:func:`elasticutils.get_es` for more details.


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch
     elasticsearch-py Elasticsearch documentation.


Indexes
=======

An `index` is a collection of documents.

Before you do anything, you need to have an index. You can create one
with `.indices.create()`.

For example:

.. code-block:: python

    es = get_es()
    es.indices.create(index='blog-index')


You can pass in settings, too. For example, you can set the refresh
interval when creating the index:

.. code-block:: python

    es.indices.create(index='blog-index', body{'refresh_interval': '5s'})


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.client.IndicesClient.create
     elasticsearch-py indices.create API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-create-index/
     Elasticsearch create index API documentation


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

To define a mapping, you use `.indices.put_mapping()`.

For example:

.. code-block:: python

    es = get_es()
    es.indices.put_mapping(
        index='blog-index',
        doc_type='blog-entry-type',
        body={
            'blog-entry-type': {
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'content': {'type': 'string'},
                    'tags': {'type': 'string'},
                    'created': {'type': 'date'}
                }
            }
        }
    )


You can also define mappings when you create the index:

.. code-block:: python

    es = get_es()
    es.indices.create(
        index='blog-index',
        body={
            'mappings': {
                'blog-entry-type': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'content': {'type': 'string'},
                    'tags': {'type': 'string'},
                    'created': {'type': 'date'}
                }
            }
        }
    )


.. Note::

   If there's a possibility of a race condition between creating the
   index and defining the mapping and some document getting indexed,
   then it's good to create the index and define the mappings at the
   same time.


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.client.IndicesClient.put_mapping
     elasticsearch-py indices.put_mapping API documentation

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

    es.index(index='blog-index', doc_type='blog-entry-type', body=entry, id=1)


If you're indexing a bunch of documents at the same time, you should
use `elasticsearch.helpers.bulk_index()`.

For example:

.. code-block:: python

    from elasticsearch.helpers import bulk_index

    es = get_es()

    entries = [{ '_id': 42, ... }, { '_id': 47, ... }]

    bulk_index(es, entries, index='blog-index', doc_type='blog-entry-type')


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.Elasticsearch.index
     elasticsearch-py index API documentation

   http://elasticsearch-py.readthedocs.org/en/latest/helpers.html#elasticsearch.helpers.bulk_index
     elasticsearch-py bulk_index API documentation

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

    es.delete(index='blog-index', doc_type='blog-entry-type', id=1)


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.Elasticsearch.delete
     elasticsearch-py delete API documentation

   http://www.elasticsearch.org/guide/reference/api/delete/
     Elasticsearch delete API documentation


Refreshing
==========

After you index documents, they're not available for searches until
after the index is refreshed. By default, the index refreshes every
second. If you need the documents to show up in searches before that,
call `indices.refresh()`.

For example:

.. code-block:: python

    es = get_es()

    es.indices.refresh(index='blog-index')


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.client.IndicesClient.refresh
     elasticsearch-py indices.refresh API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-refresh/
     Elasticsearch refresh API documentation


Delete indexes
==============

You can delete indexes with `.indices.delete()`.

For example:

.. code-block:: python

    es = get_es()

    es.indices.delete(index='blog-index')


.. seealso::

   http://elasticsearch-py.readthedocs.org/en/latest/api.html#elasticsearch.client.IndicesClient.delete
     elasticsearch-py indices.delete API documentation

   http://www.elasticsearch.org/guide/reference/api/admin-indices-delete-index/
     Elasticsearch delete index API documentation


Doing all of this with MappingTypes and Indexables
==================================================

If you're using MappingTypes, then you can do much of the above using
methods and classmethods on :py:class:`MappingType` and
:py:class:`Indexable` classes. See :ref:`mapping-type-chapter` for
more details.
