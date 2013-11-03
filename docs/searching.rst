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

:py:class:`elasticutils.S` helps you define an Elasticsearch
search.

::

    searcher = S()

This creates an `untyped` :py:class:`elasticutils.S` using the
defaults:

* uses an :py:class:`elasticsearch.client.Elasticsearch` instance
  configured to connect to ``localhost`` -- call
  :py:meth:`elasticutils.S.es` to specify connection parameters
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
instances of that type. See :ref:`mapping-type-chapter` for more about
MappingTypes.


S can be sliced to return the results you want
----------------------------------------------

By default Elasticsearch gives you the first 10 results.

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

   The slicing happens on the Elasticsearch side---it doesn't pull all
   the results back and then slice them in Python. Ew.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/from-size.html
     Elasticsearch from / size documentation


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
another roundtrip to your Elasticsearch cluster.


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
useful bits including the raw response from Elasticsearch. See
documentation for details.


Where to search
===============

Specifying connection parameters: ``es``
----------------------------------------

:py:class:`elasticutils.S` will generate an
:py:class:`elasticsearch.client.Elasticsearch` object that connects
to ``localhost`` by default. That's usually not what you want. You can use the
:py:meth:`elasticutils.S.es` method to specify the arguments used to create the
elasticsearch-py Elasticsearch object.

Examples::

    q = S().es(urls=['localhost'])
    q = S().es(urls=['localhost:9200'], timeout=10)

See :py:func:`elasticutils.get_es` for the list of arguments you
can pass in.


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
specified will do a ``match_all`` query in Elasticsearch.

.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/match-all-query.html
     Elasticsearch match_all documentation


.. _queries-queries:

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

======================  =========================
field action            elasticsearch query type
======================  =========================
(no action specified)   Term query
term                    Term query
terms                   Terms query
text                    Text query
match                   Match query [1]_
prefix                  Prefix query [2]_
gt, gte, lt, lte        Range query
range                   Range query [4]_
fuzzy                   Fuzzy query
wildcard                Wildcard query
text_phrase             Text phrase query
match_phrase            Match phrase query [1]_
query_string            Querystring query [3]_
======================  =========================


.. [1] Elasticsearch 0.19.9 renamed text queries to match queries. If
       you're using Elasticsearch 0.19.9 or later, you should use
       match and match_phrase. If you're using a version prior to
       0.19.9 use text and text_phrase.

.. [2] You can also use ``startswith``, but that's deprecated.

.. [3] When doing ``query_string`` queries, if the query text is malformed
       it'll raise a `SearchPhaseExecutionException` exception.

.. [4] The ``range`` field action is a shortcut for defining both sides of
       the range at once. The range is inclusive on both sides and accepts
       a tuple with the lower value first and upper value second.


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     Elasticsearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html
     Elasticsearch docs on term queries

   http://www.elasticsearch.org/guide/reference/query-dsl/terms-query.html
     Elasticsearch docs on terms queries

   http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
     Elasticsearch docs on text and text_phrase queries

   http://www.elasticsearch.org/guide/reference/query-dsl/match-query.html
     Elasticsearch docs on match and match_phrase queries

   http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
     Elasticsearch docs on prefix queries

   http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
     Elasticsearch docs on range queries

   http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
     Elasticsearch docs on fuzzy queries

   http://www.elasticsearch.org/guide/reference/query-dsl/wildcard-query.html
     Elasticsearch docs on wildcard queries

   http://www.elasticsearch.org/guide/reference/query-dsl/query-string-query.html
     Elasticsearch docs on query_string queries


Advanced queries: ``Q`` and ``query_raw``
=========================================

calling .query() multiple times
-------------------------------

Calling :py:meth:`elasticutils.S.query` multiple times will combine
all the queries together.


should, must and must_not
-------------------------

By default all queries must match a document in order for the document
to show up in the search results.

You can alter this behavior by flagging your queries with ``should``,
``must``, and ``must_not`` flags.

**should**

    A query added with ``should=True`` affects the score for a result,
    but it won't prevent the document from being in the result set.

    Example::

        qs = S().query(title__text='castle',
                       summary__text='castle',
                       should=True)

    If the document matches either the ``title__text`` or the
    ``summary__text`` then it's included in the results set. It
    doesn't *have* to match both.


**must**

    This is the default.

    A query added with ``must=True`` must match in order for the
    document to be in the result set.

    Example::

        qs = S().query(title__text='castle',
                       summary__text='castle')

        qs = S().query(title__text='castle',
                       summary__text='castle',
                       must=True)

    These two are equivalent. The document must match both the
    ``title__text`` and ``summary__text`` queries in order to be
    included in the result set. If it doesn't match one of them, then
    it's not included.


**must_not**

    A query added with ``must_not=True`` must NOT match in order
    for the document to be in the result set.

    Example::

        qs = (S().query(title__text='castle')
                 .query(author='castle', must_not=True))

    For a document to be included in the result set, it must match the
    ``title__text`` query and must NOT match the ``author``
    query. I.e. The title must have "castle", but the document can't
    have been written by someone with "castle" in their name.


The Q class
-----------

You can manipulate query units with the :py:class:`elasticutils.Q`
class. For example, you can incrementally build your query::

    q = Q()

    if search_authors:
        q += Q(author_name=search_text, should=True)

    if search_keywords:
        q += Q(keyword=search_text, should=True)

    q += Q(title__text=search_text, summary__text=search_text,
           should=True)


The ``+`` Python operator will combine two `Q` instances together and
return a new instance.

You can then use one or more `Q` classes in a query call::

    if search_authors:
        q += Q(author_name=search_text, should=True)

    if search_keywords:
        q += Q(keyword=search_text, should=True)

    q += Q(title__text=search_text, summary__text=search_text,
           should=True)

    s = S().query(q)


query_raw
---------

:py:meth:`elasticutils.S.query_raw` lets you explicitly define the
query portion of an Elasticsearch search.

For example::

   q = S().query_raw({'match': {'title': 'example'}})

This will override all ``.query()`` calls you've made in your
:py:class:`elasticutils.S` before and after the `.query_raw` call.

This is helpful if ElasticUtils is missing functionality you need.


adding new query actions
------------------------

You can subclass :py:class:`elasticutils.S` and add handling for
additional query actions. This is helpful in two circumstances:

1. ElasticUtils doesn't have support for that query type
2. ElasticUtils doesn't support that query type in a way you
   need---for example, ElasticUtils uses different argument values

See :py:class:`elasticutils.S` for more details on how to do this.


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
range                Range filter [5]_
prefix, startswith   Prefix filter
(no action)          Term filter
===================  ====================

.. [5] The ``range`` field action is a shortcut for defining both sides of
       the range at once. The range is inclusive on both sides and accepts
       a tuple with the lower value first and upper value second.

You can also filter on fields that have ``None`` as a value or have no
value::

    q = S().filter(language=None)

This uses the Elasticsearch Missing filter.


.. Note::

   In order to filter on fields that have ``None`` as a value, you
   have to tell Elasticsearch that the field can have null values. To
   do this, you have to add ``null_value: True`` to the mapping for
   that field.

   http://www.elasticsearch.org/guide/reference/mapping/core-types.html


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     Elasticsearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
     Elasticsearch docs for terms filter

   http://www.elasticsearch.org/guide/reference/query-dsl/range-filter.html
     Elasticsearch docs for range filter

   http://www.elasticsearch.org/guide/reference/query-dsl/prefix-filter.html
     Elasticsearch docs for prefix filter

   http://www.elasticsearch.org/guide/reference/query-dsl/term-filter.html
     Elasticsearch docs for term filter

   http://www.elasticsearch.org/guide/reference/query-dsl/missing-filter.html
     Elasticsearch docs for missing filter


Advanced filters: ``F`` and ``filter_raw``
==========================================


and vs. or
----------

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


The F class
-----------

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


filter_raw
----------

:py:meth:`elasticutils.S.filter_raw` lets you explicitly define
the filter portion of an Elasticsearch search.

For example::

    qs = S().filter_raw({'term': {'title': 'foo'}})

This will override all ``.filter()`` calls you've made in your
:py:class:`elasticutils.S` before and after the `.filter_raw` call.

This is helpful if ElasticUtils is missing functionality you need.


adding new filteractions
------------------------

You can subclass :py:class:`elasticutils.S` and add handling for
additional filter actions. This is helpful in two circumstances:

1. ElasticUtils doesn't have support for that filter type
2. ElasticUtils doesn't support that filter type in a way you
   need---for example, ElasticUtils uses different argument values

See :py:class:`elasticutils.S` for more details on how to do this.


Query-time field boosting: ``boost``
====================================

ElasticUtils allows you to specify query-time field boosts with
:py:meth:`elasticutils.S.boost`.

These boosts take effect at the time the query is executing. After the
query has executed, then the boost is applied and that becomes the
final score for the query.

This is a useful way to weight queries for some fields over others.

See :py:meth:`elasticutils.S.boost` for more details.

.. Note::

   Boosts are ignored if you use query_raw.


Ordering: ``order_by``
======================

ElasticUtils :py:meth:`elasticutils.S.order_by` lets you change the
order of the search results.

See :py:meth:`elasticutils.S.order_by` for more details.

.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/sort.html
     Elasticsearch docs on sort parameter in the Search API


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


This is implemented using the `boosting query` in Elasticsearch.
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
     Elasticsearch docs on boosting query (which are as clear as mud)


Highlighting: ``highlight``
===========================

ElasticUtils can highlight excerpts for search results.

See :py:meth:`elasticutils.S.highlight` for more details.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/highlighting.html
     Elasticsearch docs for highlight


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
     Elasticsearch docs on facets

   http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
     Elasticsearch docs on terms facet



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
     Elasticsearch docs on facets, facet_filter, and global

   http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
     Elasticsearch docs on terms facet



Facets... RAW!: ``facet_raw``
-----------------------------

Elasticsearch facets can do a lot of other things. Because of this,
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
     Elasticsearch docs on scripting

Filter and query facets
-----------------------

You can also define arbitrary facets for queries and facets as documented
in Elasticsearch's docs.

For example::

    q = (S().query(title='taco trucks')
            .facet_raw(korean_or_mexican={
                'filter': {
                    'or': [
                        {'term': {'style': 'korean'}},
                        {'term': {'style': 'mexican'}},
                    ]
                }
            }))

Then access the custom facet via the name you passed into ``facet_raw``::

  counts = q.facet_counts()
  korean_or_mexican_count = counts['korean_or_mexican']['count']

The same can be done with queries::

  q = (S().query(title='taco trucks')
        .facet_raw(korean={
            'query': {
                'term': {'style': 'korean'},
            }
        }))

.. seealso::

  http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-facets-query-facet.html
    Elasticsearch docs on query facets

  http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-facets-filter-facet.html
    Elasticsearch docs on filter facets

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
You can set the search to pass the ``explain`` flag to Elasticsearch
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
     Elasticsearch docs on explain (which are pretty bereft of
     details).
