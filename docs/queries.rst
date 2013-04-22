===========
 Searching
===========

.. contents::
   :local:


Overview
========

This chapter covers how to search with ElasticUtils.


All about S: ``S``
==================

What is S?
----------

:py:class:`elasticutils.S` helps you define an ElasticSearch
search.

::

    searcher = S()

This creates an `untyped ` :py:class:`elasticutils.S` using the
defaults:

* uses an :py:class:`pyelasticsearch.client.ElasticSearch` instance
  configured to connect to ``http://localhost:9200`` -- call ``.es()``
  to specify connection parameters
* searches across all indexes -- call
  :py:meth:`elasticutils.S.indexes` to specify indexes
* searches across all doctypes -- call
  :py:meth:`elasticutils.S.doctypes` to specify doctypes


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
called an `untyped S`. By default, search results for a `untyped S`
are returned in the form of a sequence of
:py:class:`elasticutils.DefaultMappingType` instances. You can
explicitly state that you want a sequence of dicts or lists, too. See
:ref:`queries-shapes` for more details on how to return results in
various formats.

You can also construct a `typed S` which is an `S` with a
:py:class:`elasticutils.MappingType` subclass. By default, search
results for a `typed S` are returned in the form of a sequence of
instances of that type. See :ref:`queries-mapping-type` for more about
MappingTypes.


S can be sliced to return the results you want
----------------------------------------------

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


.. Note::

   The slicing happens on the ElasticSearch side---it doesn't pull all
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
further executions of that :py:class:`elasticutils.S` won't result in
another roundtrip to your ElasticSearch cluster.


.. _queries-shapes:

S results can be returned in many shapes
----------------------------------------

An `untyped S` (e.g. ``S()``) will return instances of
:py:class:`elasticutils.DefaultMappingType` by default.

A `typed S` (e.g. ``S(Foo)``), will return instances of that type
(e.g. type ``Foo``) by default.

:py:meth:`elasticutils.S.values_list` gives you a list of
tuples. See documentation for more details.

:py:meth:`elasticutils.S.values_dict` gives you a list of dicts. See
documentation for more details.

If you use :py:meth:`elasticutils.S.execute`, you get back a
:py:class:`elasticutils.SearchResults` instance which has additional
useful bits including the raw response from ElasticSearch. See
documentation for details.


.. _queries-mapping-type:

Mapping types
=============

:py:class:`elasticutils.MappingType` lets you centralize concerns
regarding documents you're storing in your ElasticSearch index.


Lets you tie business logic to search results
---------------------------------------------

When you do searches with MappingTypes, you get back those results as
an iterable of MappingTypes by default.

For example, say you had a description field and wanted to have a
truncated version of it. You could do it this way::

    class MyMappingType(MappingType):

        # ... missing code here

        def description_truncated(self):
            return self.description[:100]

    results = S(MyMappingType).query(description__text='stormy night')

    print list(results)[0].description_truncated()


Lets you link database data to search results
---------------------------------------------

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


DefaultMappingType
------------------

The most basic MappingType is the DefaultMappingType which is returned
if you don't specify a MappingType and also don't call
:py:meth:`elasticutils.S.values_dict` or
s:py:meth:`elasticutils.S.values_list`. The DefaultMappingType lets
you access search result fields as instance attributes or as keys::

    res.description
    res['description']

The latter syntax is helpful when there are attributes defined on the
class that have the same name as the document field.


For more information
--------------------

See :py:class:`elasticutils.MappingType` for documentation on creating
MappingTypes.


Where to search
===============

Specifying connection parameters: ``es``
----------------------------------------

:py:class:`elasticutils.S` will generate an
:py:class:`pyelasticsearch.client.ElasticSearch` object that connects
to ``http://localhost:9200`` by default. That's usually not what
you want. You can use the :py:meth:`elasticutils.S.es` method to
specify the arguments used to create the ElasticSearch object.

Examples::

    q = S().es(urls=['http://localhost:9200'])
    q = S().es(urls=['http://localhost:9200'], timeout=10)

See :ref:`es-chapter` for the list of arguments you can pass in.


Specifying indexes to search: ``indexes``
-----------------------------------------

An `untyped S` will search all indexes by default.

A `typed S` will search the index returned by the
:py:meth:`elasticutils.MappingType.get_index` method.

If that's not what you want, use the
:py:meth:`elasticutils.S.indexes` method.

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
:py:meth:`elasticutils.MappingType.get_mapping_type_name` method.

If that's not what you want, then you should use the
:py:meth:`elasticutils.S.doctypes` method.

For example, this searches all doctypes::

    q = S()

This searches just the "sometype" doctype::

    q = S().doctypes('sometype')

This searches "thistype" and "thattype"::

    q = S().doctypes('thistype', 'thattype')


By default, S does a Match All
==============================

By default, :py:class:`elasticutils.S` with no filters or queries
specified will do a ``match_all`` query in ElasticSearch.

.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/match-all-query.html
     ElasticSearch match_all documentation


Queries: ``query``
==================

Queries are specified using the :py:meth:`elasticutils.S.query`
method. See those docs for API details.

ElasticUtils uses this syntax for specifying queries:

    fieldname__fieldaction=value


1. fieldname: the field the query applies to
2. fieldaction: the kind of query it is
3. value: the value to query for

The fieldname and fieldaction are separated by ``__`` (that's two
underscores).

For example::

   q = S().query(title__match='taco trucks')


will do an Elasticsearch match query on the title field for "taco
trucks".

There are many different field actions to choose from:

======================  =======================
field action            elasticsearch query
======================  =======================
(no action specified)   term query
term                    term query
text                    text query
match                   match query [1]_
prefix                  prefix query [2]_
gt, gte, lt, lte        range query
fuzzy                   fuzzy query
text_phrase             text_phrase query
match_phrase            match_phrase query [1]_
query_string            query_string query [3]_
======================  =======================


.. [1] Elasticsearch 0.19.9 renamed text queries to match queries. If
       you're using Elasticsearch 0.19.9 or later, you should use
       match and match_phrase. If you're using a version prior to
       0.19.9 use text and text_phrase.

.. [2] You can also use ``startswith``, but that's deprecated.

.. [3] When doing ``query_string`` queries, if the query text is malformed
       it'll raise a `SearchPhaseExecutionException` exception.


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html
     ElasticSearch docs on term queries

   http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
     ElasticSearch docs on text and text_phrase queries

   http://www.elasticsearch.org/guide/reference/query-dsl/match-query.html
     ElasticSearch docs on match and match_phrase queries

   http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
     ElasticSearch docs on prefix queries

   http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
     ElasticSearch docs on range queries

   http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
     ElasticSearch docs on fuzzy queries

   http://www.elasticsearch.org/guide/reference/query-dsl/query-string-query.html
     ElasticSearch docs on query_string queries


Advanced queries: ``query_raw``
===============================

:py:meth:`elasticutils.S.query_raw` lets you explicitly define the
query portion of an Elasticsearch search.

For example::

   q = S().query_raw({'match': {'title': 'example'}})

This will override all ``.query()`` calls you've made in your
:py:class:`elasticutils.S` before and after the `.query_raw` call.

This is helpful if ElasticUtils is missing functionality you need.


Filters: ``filter``
===================

Filters are specified using the :py:meth:`elasticutils.S.filter`
method. See those docs for API details.

::

   q = S().filter(language='korean')


will do a search and only return results where the language is Korean.

:py:meth:`elasticutils.S.filter` uses the same syntax for specifying
fields, actions and values as :py:meth:`elasticutils.S.query`.

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

You can do the same thing by putting both filters in the same
:py:meth:`elasticutils.S.filter` call.

For example::

   q = S().filter(style='korean', price='FREE')


Suppose you want either Korean or Mexican food. For that, you need an
"or". You can do something like this::

   q = S().filter(or_={'style': 'korean', 'style'='mexican'})


But, wow---that's icky looking and not particularly helpful!

So, we've also got an :py:meth:`elasticutils.F` class that makes this
sort of thing easier.

You can do the previous example with ``F`` like this::

   q = S().filter(F(style='korean') | F(style='mexican'))


will get you all the search results that are either "korean" or
"mexican" style.

What if you want Mexican food, but only if it's FREE, otherwise you
want Korean?::

   q = S().filter(F(style='mexican', price='FREE') | F(style='korean'))


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

ElasticUtils allows you to specify query-time field boosts with
:py:meth:`elasticutils.S.boost`.

This is a useful way to weight queries for some fields over others.

See :py:meth:`elasticutils.S.boost` for more details.


Ordering: ``order_by``
======================

ElasticUtils :py:meth:`elasticutils.S.order_by` lets you change the
order of the search results.

See :py:meth:`elasticutils.S.order_by` for more details.

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

   You can only call :py:meth:`elasticutils.S.demote` once. Calling it
   again overwrites previous calls.


This is implemented using the `boosting query` in ElasticSearch.
Anything you specify with :py:meth:`elasticutils.S.query` goes into
the `positive` section. The `negative query` and `negative boost`
portions are specified as the first and second arguments to
:py:meth:`elasticutils.S.demote`.

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

ElasticUtils can highlight excerpts for search results.

See :py:meth:`elasticutils.S.highlight` for more details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/highlighting.html
     ElasticSearch docs for highlight


.. _queries-chapter-facets-section:

Facets
======

Basic facets: ``facet``
-----------------------

::

    q = (S().query(title='taco trucks')
            .facet('style', 'location'))


will do a query for "taco trucks" and return terms facets for the
``style`` and ``location`` fields.

Note that the fieldname you provide in the
:py:meth:`elasticutils.S.facet` call becomes the facet name as well.

The facet counts are available through
:py:meth:`elasticutils.S.facet_counts`. For example::

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


The "style" and "location" facets here ONLY apply to the results of
the query and are not affected at all by the filters.

If you want your filters to apply to your facets as well, pass in the
filtered flag.

For example::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', 'location', filtered=True))


What if you want the filters to apply just to one of the facets and
not the other? You need to add them incrementally.

For example::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', filtered=True)
            .facet('location'))


What if you want the facets to apply to the entire corpus and not just
the results from the query? Use the `global_` flag.

For example::

    q = (S().query(title='taco trucks')
            .filter(style='korean')
            .facet('style', 'location', global_=True))


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
there exists :py:meth:`elasticutils.S.facet_raw` which will do
whatever you need it to. Specify key/value args by facet name.

You could do the first facet example with::

    q = (S().query(title='taco trucks')
            .facet_raw(style={'terms': {'field': 'style'}}))


One of the things this lets you do is scripted facets.

For example::

    q = (S().query(title='taco trucks')
            .facet_raw(styles={
                'field': 'style',
                'script': 'term == korean ? true : false'
            }))


.. Warning::

   If for some reason you have specified a facet with the same name
   using both :py:meth:`elasticutils.S.facet` and
   :py:meth:`elasticutils.S.facet_raw`, the facet_raw stuff will
   override the facet stuff.


.. seealso::

   http://www.elasticsearch.org/guide/reference/modules/scripting.html
     ElasticSearch docs on scripting


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
with :py:meth:`elasticutils.S.explain`.

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


More like this: ``MLT``
=======================

ElasticUtils exposes ElasticSearch More Like This API with the `MLT`
class.

For example::

    mlt = MLT(2034, index='addon_index', doctype='addon')


This creates an `MLT` that will return documents that are like
document with id 2034 of type `addon` in the `addon_index`.

You can pass it an `S` instance and the `MLT` will derive the index,
doctype, ElasticSearch object, and also use the search specified by
the `S` in the body of the More Like This request. This allows you to
get documents like the one specified that also meet query and filter
criteria. For example::

    s = S().filter(product='firefox')
    mlt = MLT(2034, s=s)


See :py:class:`MLT` for more details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/more-like-this.html
     ElasticSearch guide on More Like This API

   http://www.elasticsearch.org/guide/reference/query-dsl/mlt-query.html
     ElasticSearch guide on the moreLikeThis query which specifies the
     additional parameters you can use.

   http://pyelasticsearch.readthedocs.org/en/latest/api/#pyelasticsearch.ElasticSearch.more_like_this
     pyelasticsearch documentation for MLT
