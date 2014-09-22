
============================================================
 Migrating from Elasticsearch 0.90 to 1.x with ElasticUtils
============================================================

.. Note::

   This is a work in progress and probably doesn't cover everything.


Summary
=======

There are a bunch of API-breaking changes between Elasticsearch 0.90
and 1.x. Because of this, it's really tricky to get over this hump
without having downtime.

This document covers a high-level walk through for upgrading from
Elasticsearch 0.90 to 1.x and the steps you should take to reduce
your downtime.

.. Note::

   "1.x" covers 1.0, 1.1 and 1.2.


Steps
=====

Each of these steps should result in a working system. Do them one at
a time and test everything in between.

1. Upgrade to ElasticUtils 0.9.1

   You must use elasticsearch-py version 0.4.5--don't use a later version!

2. Upgrade your Elasticsearch cluster to version 0.90.13

3. Upgrade to ElasticUtils 0.10.1

   You will need to update elasticsearch-py past 0.4.5. The latest version
   should work fine.

4. Make any changes to your code so that it works with both Elasticsearch
   0.90 and 1.x

   There are some tricky things here, see the :ref:`tricky-things` section.

5. Upgrade to Elasticsearch 1.x


At that point, you should be using a recent version of the
elasticsearch-py library and a recent version of Elasticsearch and
should be all set.


Resources
=========

.. seealso::

   http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/breaking-changes.html
     Breaking changes when migrating to Elasticsearch 1.0

   http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/_deprecations.html
     Deprecated features when migrating to Elasticsearch 1.0


.. _tricky-things:

Tricky things
=============

There are a few tricky differences between Elasticsearch 0.90 and 1.0 that
will affect your code.


Changes with ``.values_dict()`` and ``.values_list()``
------------------------------------------------------

Explanation
~~~~~~~~~~~

In Elasticsearch 1.x, you get back different shapes of things depending
on whether you specify "fields". To smooth this out and normalize the
differences between Elasticsearch 0.90 and 1.x, ElasticUtils now **always**
passes in ``fields`` property when you use
:py:meth:`elasticutils.S.values_list` and
:py:meth:`elasticutils.S.values_dict`.

Let's show some code to illustrate the new behavior.

First, a bunch of setup:

    >>> from elasticutils import get_es, S
    >>> from elasticsearch.helpers import bulk_index
    >>> URL = 'localhost'
    >>> INDEX = 'fooindex'
    >>> BOOK_DOCTYPE = 'book'
    >>> PERSON_DOCTYPE = 'person'
    >>> es = get_es(urls=[URL])
    >>> es.indices.delete(index=INDEX, ignore=404)

Now define the two document mappings we're going to use: book and person.
Book has no stored fields. Person has two.

    >>> mapping = {
    ...    BOOK_DOCTYPE: {
    ...        'properties': {
    ...            'id': {'type': 'integer'},
    ...            'title': {'type': 'string'},
    ...            'tags': {'type': 'string'},
    ...            }
    ...        },
    ...    PERSON_DOCTYPE: {
    ...        'properties': {
    ...            'id': {'type': 'integer', 'store': True},
    ...            'name': {'type': 'string', 'store': True},
    ...            'weight': {'type': 'integer'}
    ...        }
    ...    }
    ... }

Create the index with the mappings, add some books and add some people.

    >>> es.indices.create(INDEX, body={'mappings': mapping})
    >>> books = [
    ...    {'_id': 1, 'id': 1, 'title': '10 Balloons', 'tags': ['kids', 'hardcover']},
    ...    {'_id': 2, 'id': 2, 'title': 'Puppies', 'tags': ['animals']},
    ...    {'_id': 3, 'id': 3, 'title': 'Dictionary', 'tags': ['reference']},
    ... ]
    >>> bulk_index(es, books, index=INDEX, doc_type=BOOK_DOCTYPE)
    (3, [])
    >>> people = [
    ...    {'_id': 1, 'id': 1, 'name': 'Bob', 'weight': 40},
    ...    {'_id': 2, 'id': 2, 'name': 'Jim', 'weight': 44},
    ...    {'_id': 3, 'id': 3, 'name': 'Jim Bob', 'weight': 42},
    ... ]
    >>> bulk_index(es, people, index=INDEX, doc_type=PERSON_DOCTYPE)
    [...]
    >>> es.indices.refresh(index=INDEX)
    [...]

Now let's do some queries so we can see how things work now.

Let's build a ``basic_s`` that looks at our Elasticsearch cluster and
the index. Also a ``book_s`` and a ``person_s``.

    >>> basic_s = S().es(urls=[URL]).indexes(INDEX)
    >>> book_s = basic_s.doctypes(BOOK_DOCTYPE)
    >>> person_s = basic_s.doctypes(PERSON_DOCTYPE)

How many documents are in our index?

    >>> basic_s.count()
    6

Call ``.values_list()`` on books which has no stored fields so we get back
the ``_id`` and ``_type`` for each document returned and all values are lists:

    >>> list(book_s.values_list())
    [([u'1'], [u'book']), ([u'2'], [u'book']), ([u'3'], [u'book'])]

``.values_list('id')`` on books, so we get id returned and all values are
lists:

    >>> list(book_s.values_list('id'))
    [([1],), ([2],), ([3],)]

``.values_list()`` on persons which does have stored fields (id and
name, but not weight), so we get the stored fields returned and all
values are lists:

    >>> list(person_s.values_list())
    [([1], [u'Bob']), ([2], [u'Jim']), ([3], [u'Jim Bob'])]

``.values_list('id')`` on persons which works just like books because
we've specified which fields we want back:

    >>> list(person_s.values_list('id'))
    [([1],), ([2],), ([3],)]


The same goes for ``.values_dict()``.


What you need to do
~~~~~~~~~~~~~~~~~~~

1. If you have calls to ``.values_list()`` and ``.values_dict()`` that
   don't specify any fields, then you either need to change the
   mapping and store the fields you want back, or change the calls so
   they specify the fields you want back.

2. Every time you use results from a ``.values_list()`` or ``.values_dict()`` call,
   you need to change it to always treat the values as lists.
