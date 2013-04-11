================
Searching with S
================

.. contents::
   :local:


Overview
========

ElasticUtils makes querying and filtering and collecting facets from
ElasticSearch simple.

For example::

   q = (S().es(urls=['http://localhost:9200'])
           .indexes('addon_index')
           .doctypes('addon')
           .filter(product='firefox')
           .filter(version='4.0', platform='all')
           .query(title='Example')
           .facet(products={'field': 'product', 'global': True})
           .facet(versions={'field': 'version'})
           .facet(platforms={'field': 'platform'})
           .facet(types={'field': 'type'}))


The ElasticSearch REST API curl would look like this::

    $ curl -XGET 'http://localhost:9200/addon_index/addon/_search' -d '{
    'query': {'term': {'title': 'Example'}},
    'filter': {'and': [{'term': {'product': 'firefox'}},
                       {'term': {'platform': 'all'}},
                       {'term': {'version': '4.0'}}]},
    'facets': {
       'platforms': {
           'facet_filter': {
               'and': [
                   {'term': {'product': 'firefox'}},
                   {'term': {'platform': 'all'}},
                   {'term': {'version': '4.0'}}]},
           'field': 'platform'},
       'products': {
           'facet_filter': {
               'and': [
                   {'term': {'product': 'firefox'}},
                   {'term': {'platform': 'all'}},
                   {'term': {'version': '4.0'}}]},
           'field': 'product',
           'global': True},
       'types': {
           'facet_filter': {
               'and': [
                   {'term': {'product': 'firefox'}},
                   {'term': {'platform': 'all'}},
                   {'term': {'version': '4.0'}}]},
           'field': 'type'},
       'versions': {
           'facet_filter': {
               'and': [
                   {'term': {'product': 'firefox'}},
                   {'term': {'platform': 'all'}},
                   {'term': {'version': '4.0'}}]},
           'field': 'version'}}
    }
    '

That's it!

For the rest of this chapter, when we translate ElasticUtils queries
to their equivalent ElasticSearch REST API, we're going to use a
shorthand and only talk about the body of the request which we'll call
the `ElasticSearch JSON`.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/
     ElasticSearch docs on api

   http://www.elasticsearch.org/guide/reference/api/search/
     ElasticSearch docs on search api

   http://curl.haxx.se/
     Documentation on curl


All about S: ``S``
==================

What is S?
----------

:py:class:`elasticutils.S` is the class that you instantiate to define
an ElasticSearch search. For example::

    searcher = S()

This creates an :py:class:`elasticutils.S` with using the defaults:

* uses an :py:class:`pyelasticsearch.client.ElasticSearch` instance
  configured to connect to ``http://localhost:9200`` -- call ``.es()``
  to specify connection parameters
* searches across all indexes -- call :py:meth:`elasticutils.S.indexes()` to specify
  indexes
* searches across all doctypes -- call :py:meth:`elasticutils.S.doctypes()` to specify
  doctypes


S is chainable
--------------

:py:class:`elasticutils.S` has methods that return a new S instance
with the additional specified criteria. In this way S is chainable and
you can reuse S objects for your searches.

For example::

   s1 = S()

   s2 = s1.query(content__text='tabs')

   s3 = s2.filter(awesome=True)

   s4 = s2.filter(awesome=False)

`s1`, `s2`, and `s3` are all different `S` objects. `s1` is a match
all.

`s2` has a query.

`s3` has everything in `s2` with a ``awesome=True`` filter.

`s4` has everything in `s2` with a ``awesome=False`` filter.


S can be typed and untyped
--------------------------

When you create an :py:class:`elasticutils.S` with no type, it's
called an `untyped S`.

If you don't call :py:meth:`elasticutils.S.values_dict()` or
:py:meth:`elasticutils.S.values_list()`, then your search results are
in the form of a sequence of
:py:class:`elasticutils.DefaultMappingType` instances. More about this
in :ref:`queries-mapping-type`.

You can also construct a `typed S` which is an S with a
:py:class:`elasticutils.MappingType` subclass. For example::

    from elasticutils import MappingType, S

    class MyMappingType(MappingType):
        @classmethod
        def get_index(cls):
            return 'sumo_index'

        @classmethod
        def get_mapping_type_name(cls):
            return 'mymappingtype'


    results = (S(MyMappingType).es(urls=['http://localhost:9200'])
                               .query(title__text='plugins'))


``results`` will be an iterable of MyMappingType instances---one for
each search result.


S can be sliced
---------------

By default ElasticSearch gives you the first 10 results.

If you want something different than that, :py:class:`elasticutils.S`
supports slicing allowing you to get back the specific results you're
looking for.

For example::

    some_s = S()

    results = some_s[:10]    # returns first 10 results
    results = some_s[10:20]  # returns results 10 through 19


The slicing is chainable, too::

    some_s = S()[:10]

    first_ten_pitchers = some_s.filter(position='pitcher')
    first_ten_catchers = some_s.filter(position='catcher')


.. Note::

   The slice happens on the ElasticSearch side---it doesn't pull all
   the results back and then slice them in Python. Ew.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/from-size.html
     ElasticSearch from / size documentation


S is lazy
---------

The search won't execute until you do one of the following:

1. use the :py:class:`elasticutils.S` in an iterable context
2. call :py:func:`len` on a :py:class:`elasticutils.S`
3. call the :py:meth:`elasticutils.S.execute`,
   :py:meth:`elasticutils.S.all`,
   :py:meth:`elasticutils.S.count` or
   :py:meth:`elasticutils.S.facet_counts` methods

Once you execute the search, then it will cache the results and
further uses of that :py:class:`elasticutils.S` will operate on the
same results.


S results can be returned in many shapes
----------------------------------------

If you have a `typed S` (e.g. ``S(MappingType)``), then by default,
results will be instances of that type.

If you have an `untyped S` (e.g. ``S()``), then by default, results
will be DefaultMappingType.

:py:meth:`elasticutils.S.values_list()` gives you a list of
tuples. See documentation for more details.

:py:meth:`elasticutils.S.values_dict()` gives you a list of dicts. See
documentation for more details.

If you use :py:meth:`elasticutils.S.execute()`, you get back a
:py:class:`elasticutils.SearchResults` instance which has additional
useful bits including the raw response from ElasticSearch. See
documentation for details.


.. _queries-mapping-type:

Mapping types
=============

:py:class:`elasticutils.MappingType` gives you a way to centralize
concerns regarding documents you're storing in your ElasticSearch
index. When you do searches with MappingTypes, you get back those
results as an iterable of MappingTypes by default.

For example, say you had a description field and wanted to have a
truncated version of it. You could do it this way::

    class MyMappingType(MappingType):

        # ... missing code here

        def description_truncated(self):
            return self.description[:100]

    results = S(MyMappingType).query(description__text='stormy night')

    print list(results)[0].description_truncated()


You can relate a MappingType to a database model allowing you to link
documents in the ElasticSearch index back to their origins in a
lazy-loading way. This is done by subclassing MappingType and
implementing the ``get_object()`` method. You can then access the
origin using the ``object`` property.

For example::

    class MyMappingType(MappingType):

        # ... missing code here

        def get_object(self):
            return self.get_model().objects.get(pk=self._id)

    results = S(MyMappingType).filter(height__gte=72)[:1]

    first = list(results)[0]

    # This prints "height" which comes from the ElasticSearch
    # document
    print first.height

    # This prints "height" which comes from the database data
    # that the ElasticSearch document is based on. This is the
    # first time ``.object`` is used, so it does the db hit
    # here.
    print first.object.height


The most basic MappingType is the DefaultMappingType which is returned
if you don't specify a MappingType and also don't call
:py:meth:`elasticutils.S.values_dict()` or
:py:meth:`elasticutils.S.values_list()`. The DefaultMappingType lets
you access search result fields as instance attributes or as keys::

    res.description
    res['description']

The latter syntax is helpful when there are attributes defined on the
class that have the same name as the document field.

See :py:class:`elasticutils.MappingType` for documentation on creating
MappingTypes.


What to search
==============

Specifying connection parameters: ``es``
----------------------------------------

:py:class:`elasticutils.S` will generate an
:py:class:`pyelasticsearch.client.ElasticSearch` object that connects
to ``http://localhost:9200`` by default. That's usually not what
you want. You can use the :py:meth:`elasticutils.S.es()` method to
specify the arguments used to create the ElasticSearch object.

For example::

    ES_URLS = ['http://localhost:9200']

    q = S().es(urls=ES_URLS)
    q = S().es(urls=ES_URLS, timeout=10)

See :ref:`es-chapter` for the list of arguments you can pass in.


Specifying indexes to search: ``indexes``
-----------------------------------------

An `untyped S` will search all indexes by default.

A `typed S` will search the index returned by the
:py:meth:`elasticutils.MappingType.get_index()` method.

If that's not what you want, use the
:py:meth:`elasticutils.S.indexes()` method.

For example, this searches all indexes::

    q = S()

This searches just "someindex"::

    q = S().indexes('someindex')

This searches "thisindex" and "thatindex"::

    q = S().indexes('thisindex', 'thatindex')



Specifying doctypes to search: ``doctypes``
-------------------------------------------

An `untyped S` will search all doctypes by default.

A `typed S` will search the doctype returned by the
:py:meth:`elasticutils.MappingType.get_mapping_type_name()` method.

If that's not what you want, then you should use the
:py:meth:`elasticutils.S.doctypes()` method.

For example, this searches all doctypes::

    q = S()

This searches just the "sometype" doctype::

    q = S().doctypes('sometype')

This searches "thistype" and "thattype"::

    q = S().doctypes('thistype', 'thattype')


Match All
=========

By default, :py:class:`elasticutils.S` with no filters or queries
specified will do a ``match_all`` query in ElasticSearch.

.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/match-all-query.html
     ElasticSearch match_all documentation


Queries vs. Filters
===================

A search can contain multiple queries and multiple filters. The two
things are very different.

A filter determines whether a document is in the results set or
not. If you do a term filter on whether field `foo` has value `bar`,
then the result set ONLY has documents where `foo` has value `bar`.
Filters are fast and filter results are cached in ElasticSearch when
appropriate.

A query affects the score for a document. If you do a term query on
whether field `foo` has value `bar`, then the result set will score
documents where the query holds true higher than documents where the
query does not hold true. Queries are slower than filters and
query results are not cached in ElasticSearch.

The other place where this affects things is when you specify
facets. See :ref:`queries-chapter-facets-section` for details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch Filters and Caching notes


Queries: ``query``
==================

The query is specified by keyword arguments to the
:py:meth:`elasticutils.S.query()` method. The key of the keyword
argument is parsed splitting on ``__`` (that's two underscores) with
the first part as the "field" and the second part as the "field
action".

For example::

   q = S().query(title='taco trucks')


will do an elasticsearch term query for "taco trucks" in the title field.

And::

   q = S().query(title__text='taco trucks')


will do a text query instead of a term query.

There are many different field actions to choose from:

======================  =======================
field action            elasticsearch query
======================  =======================
(no action specified)   term query
term                    term query
text                    text query
prefix                  prefix query [1]_
gt, gte, lt, lte        range query
fuzzy                   fuzzy query
text_phrase             text_phrase query
query_string            query_string query [2]_
======================  =======================


.. [1] You can also use ``startswith``, but that's deprecated.

.. [2] When doing ``query_string`` queries, if the query text is malformed
   it'll raise a `SearchPhaseExecutionException` exception.


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html
     ElasticSearch docs on term queries

   http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
     ElasticSearch docs on text and text_phrase queries

   http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
     ElasticSearch docs on prefix queries

   http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
     ElasticSearch docs on range queries

   http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
     ElasticSearch docs on fuzzy queries

   http://www.elasticsearch.org/guide/reference/query-dsl/query-string-query.html
     ElasticSearch docs on query_string queries


Filters: ``filter``
===================

::

   q = (S().query(title='taco trucks')
           .filter(style='korean'))


will do a query for "taco trucks" in the title field and filter on the
style field for 'korean'. This is how we find Korean Taco Trucks.

As with :py:meth:`elasticutils.S.query()`,
:py:meth:`elasticutils.S.filter()` allow for you to specify field
actions for the filters:

===================  ====================
field action         elasticsearch filter
===================  ====================
in                   Terms filter
gt, gte, lt, lte     Range filter
prefix, startswith   Prefix filter
(no action)          Term filter
===================  ====================


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
     ElasticSearch docs for terms filter

   http://www.elasticsearch.org/guide/reference/query-dsl/range-filter.html
     ElasticSearch docs for range filter

   http://www.elasticsearch.org/guide/reference/query-dsl/prefix-filter.html
     ElasticSearch docs for prefix filter

   http://www.elasticsearch.org/guide/reference/query-dsl/term-filter.html
     ElasticSearch docs for term filter


Advanced filters: ``filter`` and ``F``
======================================

Calling filter multiple times is equivalent to an "and"ing of the
filters.

For example::

   q = (S().filter(style='korean')
           .filter(price='FREE'))

will do a query for style 'korean' AND price 'FREE'. Anything that has
a style other than 'korean' or a price other than 'FREE' is removed
from the result set.

This translates to::

   {'filter': {
       'and': [
           {'term': {'style': 'korean'}},
           {'term': {'price': 'FREE'}}
       ]}
   }


in elasticutils JSON.

You can do the same thing by putting both filters in the same
:py:meth:`elasticutils.S.filter()` call.

For example::

   q = S().filter(style='korean', price='FREE')


that also translates to::

   {'filter': {
       'and': [
           {'term': {'style': 'korean'}},
           {'term': {'price': 'FREE'}}
       ]}
   }


in elasticutils JSON.

Suppose you want either Korean or Mexican food. For that, you need an
"or".

You can do something like this::

   q = S().filter(or_={'style': 'korean', 'style'='mexican'})


That translates to::

   {'filter': {
       'or': [
           {'term': {'style': 'korean'}},
           {'term': {'style': 'mexican'}}
       ]}
   }


But, that's kind of icky looking.

So, we've also got an :py:meth:`elasticutils.F` class that makes this
sort of thing easier.

You can do the previous example with ``F`` like this::

   q = S().filter(F(style='korean') | F(style='mexican'))


will get you all the search results that are either "korean" or
"mexican" style.

That translates to::

   {'filter': {
       'or': [
           {'term': {'style': 'korean'}},
           {'term': {'style': 'mexican'}}
       ]}
   }


What if you want Mexican food, but only if it's FREE, otherwise you
want Korean?::

   q = S().filter(F(style='mexican', price='FREE') | F(style='korean'))


That translates to::

   {'filter': {
       'or': [
           {'and': [
               {'term': {'price': 'FREE'}},
               {'term': {'style': 'mexican'}}
           ]},
           {'term': {'style': 'korean'}}
       ]}
   }


F supports ``&`` (and), ``|`` (or) and ``~`` (not) operations.

Additionally, you can create an empty F and build it incrementally::

    qs = S()
    f = F()
    if some_crazy_thing:
        f &= F(price='FREE')
    if some_other_crazy_thing:
        f |= F(style='mexican')

    qs = qs.filter(f)

If neither `some_crazy_thing` or `some_other_crazy_thing` are
``True``, then F will be empty. That's ok because empty filters are
ignored.

.. Note::

   If ElasticUtils doesn't have support for filters you need, you can
   subclass :py:class:`elasticutils.S` and add ``process_filter_X``
   methods. See the documentation for :py:class:`elasticutils.S` for
   more details.


Query-time field boosting: ``boost``
====================================

ElasticSearch allows you to boost scores for fields specified in the
search query at query-time.

ElasticUtils allows you to specify query-time field boosts with
:py:meth:`elasticutils.S.boost()`. It takes a set of arguments where
the keys are either field names or field name + ``__`` + field action.

Here's an example::

    q = (S().query(title='taco trucks',
                   description__text='awesome')
            .boost(title=4.0, description__text=2.0))

If the key is a field name, then the boost will apply to all query
bits that have that field name. For example::

    q = (S().query(title='trucks',
                   title__prefix='trucks',
                   title__fuzzy='trucks')
            .boost(title=4.0))

applies a 4.0 boost to all three query bits because all three query
bits are for the ``title`` field name.

If the key is a field name and field action, then the boost will apply
only to that field name and field action. For example::

    q = (S().query(title='trucks',
                   title__prefix='trucks',
                   title__fuzzy='trucks')
            .boost(title__prefix=4.0))

will only apply the 4.0 boost to ``title__prefix``.


Ordering: ``order_by``
======================

You can change the  order search results by specified fields::

    q = (S().query(title='trucks')
            .order_by('title')

This orders search results by the `title` field in ascending order.

If you want to sort by descending order, prepend a ``-``::

    q = (S().query(title='trucks')
            .order_by('-title')

You can also sort by the computed field ``_score``.

.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/sort.html
     ElasticSearch docs on sort parameter in the Search API


Demoting: ``demote``
====================

You can demote documents that match query criteria::

    q = (S().query(title='trucks')
            .demote(0.5, description__text='gross'))

This does a query for trucks, but demotes any that have "gross" in the
description with a fraction boost of 0.5.

.. Note::

   You can only call :py:meth:`elasticutils.S.demote()` once. Calling
   it again overwrites previous calls.

This is implemented using the `boosting query` in ElasticSearch.
Anything you specify with :py:meth:`elasticutils.S.query()` goes into
the `positive` section. The `negative query` and `negative boost`
portions are specified as the first and second arguments to
:py:meth:`elasticutils.S.demote()`.

.. Note::

   Order doesn't matter. So::

       q = (S().query(title='trucks')
               .demote(0.5, description__text='gross'))

   does the same thing as::

       q = (S().demote(0.5, description__text='gross')
               .query(title='trucks'))

.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/boosting-query.html
     ElasticSearch docs on boosting query (which are as clear as mud)


Highlighting: ``highlight``
===========================

ElasticUtils allows you to highlight excerpts that match the query
using the :py:meth:`elasticutils.S.highlight()` transform. This
returns data that will be in every item in the search results list as
``_highlight``.

For example, let's do a query on a search corpus of knowledge base
articles for articles with the word "crash" in them::

    q = (S().query(title__text='crash', content__text='crash')
            .highlight('title', 'content'))

    for result in q:
        print result._highlight['title']
        print result._highlight['content']

This will print two lists. The first is highlighted fragments from the
title field. The second is highlighted fragments from the content
field.

Highlighting is done in ElasticSearch and covers all the query
bits. So if you had a document like this::

    {
        "title": "How not to be seen",
        "content": "The first rule of how not to be seen: don't stand up."
    }

And did this query::

    q = (S().query(title__text="rule seen", content__text="rule seen")
            .highlight('title', 'content'))

Then the highlights you'd get back would be:

* title: ``to be <em>seen</em>``
* content: ``first <em>rule</em> of how not to be <em>seen</em>: don't
  stand up.``

The "highlight" default is to wrap the matched text with ``<em>`` and
``</em>``. You can change this by passing in ``pre_tags`` and
``post_tags`` options::

    q = (S().query(title__text='crash', content__text='crash')
            .highlight('title', 'content',
                       pre_tags=['<b>'],
                       post_tags=['</b>']))

If you need to clear the highlight, call
:py:meth:`elasticutils.S.highlight()` with ``None``. For example, this
search won't highlight anything::

    q = (S().query(title__text='crash')
            .highlight('title')          # highlights 'title' field
            .highlight(None))            # clears highlight


.. Note::

   Make sure the fields you're highlighting are indexed correctly.
   Check the ElasticSearch documentation for details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/highlighting.html
     ElasticSearch docs for highlight


.. _queries-chapter-facets-section:

Facets: ``facet``
=================

Basic facets
------------

::

    q = (S().query(title='taco trucks')
            .facet('style', 'location'))


will do a query for "taco trucks" and return terms facets for the
``style`` and ``location`` fields.

That translates to::

    {'query': {'term': {'title': 'taco trucks'}},
     'facets': {
         'style': {'terms': {'field': 'style'}},
         'location': {'terms': {'field': 'location'}}
         }
    }

Note that the fieldname you provide in the
:py:meth:`elasticutils.S.facet()` call becomes the facet name as well.

The facet counts are available through
:py:meth:`elasticutils.S.facet_counts()`. For example::

    q = (S().query(title='taco trucks')
            .facet('style', 'location'))
    counts = q.facet_counts()


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/facets/
     ElasticSearch docs on facets

   http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
     ElasticSearch docs on terms facet



Facets and scope (filters and global)
-------------------------------------

What happens if your search includes filters?

Here's an example::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', 'location'))


That translates to this::

    {'query': {'term': {'title': 'taco trucks'}},
     'filter': {'term': {'style': 'korean'}},
     'facets': {
         'style': {
             'terms': {'field': 'style'}
             },
         'location': {
             'terms': {'field': 'location'}
             }
         }
     }


The "style" and "location" facets here ONLY apply to the results of
the query and are not affected at all by the filters.

If you want your filters to apply to your facets as well, pass in the
filtered flag::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', 'location', filtered=True))


That translates to this::

    {'query': {'term': {'title': 'taco trucks'}},
     'filter': {'term': {'style': 'korean'}},
     'facets': {
         'styles': {
             'facet_filter': {'term': {'style': 'korean'}},
             'terms': {'field': 'style'}
             },
         'locations': {
             'facet_filter': {'term': {'style': 'korean'}},
             'terms': {'field': 'location'}
             }
         }
    }


Notice how there's an additional `facet_filter` component to the
facets and it contains the contents of the original `filter`
component.

What if you want the filters to apply just to one of the facets and
not the other? You need to add them incrementally::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', filtered=True)
            .facet('location'))

That translates to this::

    {'query': {'term': {'title': 'taco trucks'}},
     'filter': {'term': {'style': 'korean'}},
     'facets': {
         'style': {
             'facet_filter': {'term': {'style': 'korean'}},
             'terms': {'field': 'style'}
             },
         'location': {
             'terms': {'field': 'location'}
             }
         }
     }


What if you want the facets to apply to the entire corpus and not just
the results from the query? Use the `global_` flag::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', 'location', global_=True))


That translates to this::

    {'query': {'term': {'title': 'taco trucks'}},
     'filter': {'term': {'style': 'korean'}},
     'facets': {
        'style': {
             'global': True,
             'terms': {'field': 'style'}
             },
        'location': {
             'global': True,
             'terms': {'field': 'location'}
             }
        }
    }

.. Note::

   The flag name is `global_` with an underscore at the end. Why?
   Because `global` with no underscore is a Python keyword.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/facets/
     ElasticSearch docs on facets, facet_filter, and global

   http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
     ElasticSearch docs on terms facet



Facets... RAW!: ``facet_raw``
-----------------------------

ElasticSearch facets can do a lot of other things. Because of this,
there exists :py:meth:`elasticutils.S.facet_raw()` which will do
whatever you need it to. Specify key/value args by facet name.

For example, you can do the first facet example by::

    q = (S().query(title='taco trucks')
            .facet_raw(style={'terms': {'field': 'style'}}))

One of the things this lets you do is scripted facets. For example::

    q = (S().query(title='taco trucks')
            .facet_raw(styles={
                'field': 'style',
                'script': 'term == korean ? true : false'
            }))

That translates to::

    {'query': {'term': {'title': 'taco trucks'}},
     'facets': {
         'styles': {
             'field': 'style',
             'script': 'term == korean ? true : false'
             }
         }
    }


.. Warning::

   If for some reason you have specified a facet with the same name
   using both :py:meth:`elasticutils.S.facet()` and
   :py:meth:`elasticutils.S.facet_raw()`, the facet_raw stuff will
   override the facet stuff.


.. seealso::

   http://www.elasticsearch.org/guide/reference/modules/scripting.html
     ElasticSearch docs on scripting


Counts: ``count``
=================

Total hits can be found by using :py:meth:`elasticutils.S.count()`.
For example::

    q = S().query(title='taco trucks')
    count = q.count()


.. Note::

   Don't use Python's ``len`` built-in on the `S` instance if you want
   the total number of documents in your index that matches your
   search.

   This::

       q = S()
       ...
       q.count()

   asks ElasticSearch how many documents in the index match your
   search.

   This::

       q = S()
       ...
       len(q)

   performs the search, gets back as many documents as specified by
   the limits of your search, and returns the length of that list of
   documents which is **not** the total number of results in
   ElasticSearch that match your search.


.. _scores-and-explanations:

Scores and explanations
=======================

Seeing the score: _score
------------------------

Wondering what the score for a document was? ElasticUtils puts that in
the ``_score`` on the search result. For example, let's search an
index that holds knowledge base articles for ones with the word
"crash" in them and print out the scores::

    q = S().query(title__text='crash', content__text='crash')

    for result in q:
        print result._score

This works regardless of what form the search results are in.


Getting an explanation: ``explain``
-----------------------------------

Wondering why one document shows up higher in the results than another
that should have shown up higher? Wonder how that score was computed?
You can set the search to pass the ``explain`` flag to ElasticSearch
with :py:meth:`elasticutils.S.explain()`.

This returns data that will be in every item in the search results
list as ``_explanation``.

For example, let's do a query on a search corpus of knowledge base
articles for articles with the word "crash" in them::

    q = (S().query(title__text='crash', content__text='crash')
            .explain())

    for result in q:
        print result._explanation


This works regardless of what form the search results are in.

.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/explain.html
     ElasticSearch docs on explain (which are pretty bereft of
     details).


API
===

The S class
-----------

.. autoclass:: elasticutils.S

   .. automethod:: elasticutils.S.__init__

   **Chaining transforms**

       .. automethod:: elasticutils.S.query

       .. automethod:: elasticutils.S.filter

       .. automethod:: elasticutils.S.order_by

       .. automethod:: elasticutils.S.boost

       .. automethod:: elasticutils.S.demote

       .. automethod:: elasticutils.S.facet

       .. automethod:: elasticutils.S.facet_raw

       .. automethod:: elasticutils.S.highlight

       .. automethod:: elasticutils.S.values_list

       .. automethod:: elasticutils.S.values_dict

       .. automethod:: elasticutils.S.es

       .. automethod:: elasticutils.S.indexes

       .. automethod:: elasticutils.S.doctypes

       .. automethod:: elasticutils.S.explain

   **Methods to override if you need different behavior**

       .. automethod:: elasticutils.S.get_es

       .. automethod:: elasticutils.S.get_indexes

       .. automethod:: elasticutils.S.get_doctypes

   **Methods that force evaluation**

       .. automethod:: elasticutils.S.__iter__

       .. automethod:: elasticutils.S.__len__

       .. automethod:: elasticutils.S.all

       .. automethod:: elasticutils.S.count

       .. automethod:: elasticutils.S.execute

       .. automethod:: elasticutils.S.facet_counts


The F class
-----------

.. autoclass:: elasticutils.F
   :members:


The MappingType class
---------------------

.. autoclass:: elasticutils.MappingType

   .. automethod:: elasticutils.MappingType.from_results

   .. automethod:: elasticutils.MappingType.get_object

   .. automethod:: elasticutils.MappingType.get_index

   .. automethod:: elasticutils.MappingType.get_mapping_type_name

   .. automethod:: elasticutils.MappingType.get_model


The SearchResults class
-----------------------

.. autoclass:: elasticutils.SearchResults
   :members:
