==========================
Querying with ElasticUtils
==========================

.. contents::
   :local:


Overview
========

ElasticUtils makes querying and filtering and collecting facets from
ElasticSearch simple.

For example:

.. code-block:: python

   q = (S().filter(product='firefox')
           .filter(version='4.0', platform='all')
           .facet(products={'field': 'product', 'global': True})
           .facet(versions={'field': 'version'})
           .facet(platforms={'field': 'platform'})
           .facet(types={'field': 'type'})
           .doctypes('addon')
           .indexes('addon_index')
           .query(title='Example'))


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
           'field': 'version'}},
    'fields': ['id']
    }
    '

That's it!

For the rest of this chapter, when we translate ElasticUtils queries
to their equivalent elasticsearch REST API, we're going to use a
shorthand and only talk about the body of the request which we'll call
the `elasticsearch JSON`.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/
     ElasticSearch docs on api

   http://www.elasticsearch.org/guide/reference/api/search/
     ElasticSearch docs on search api

   http://curl.haxx.se/
     Documentation on curl


All about S
===========

Basic untyped S
---------------

`S` is the class that you instantiate to create a search. For example::

    searcher = S()


`S` has a bunch of methods that all return a new `S` with additional
accumulated search criteria.

For example::

   s1 = S()

   s2 = s1.query(content__text='tabs')

   s3 = s2.filter(awesome=True)

   s4 = s2.filter(awesome=False)

`s1`, `s2`, and `s3` are all different `S` objects. `s1` is a match
all.

`s2` has a query.

`s3` has everything in `s2` plus a ``awesome=True`` filter.

`s4` has everything in `s2` with a ``awesome=False`` filter.


Typed S and creating types
--------------------------

You can also construct a `typed S` which is an `S` with a model
class. For example::

   S(Model)


The model class needs to follow Django's ORM model system, but you can
stub out the required bits even if you're not using Django.

1. The model class needs a class-level attribute ``objects``.
2. The ``objects`` attribute needs a method ``filter``.
3. The ``filter`` method has a ``id__in`` argument which takes an
   iterable of ids.

For example::

    class FakeModelManager(object):
        def filter(self, id__in):
            # returns list of FakeModel objects with those ids

    class FakeModel(object):
        objects = FakeModelManager()


Then you can create an `S`::

    searcher = S(FakeModel)


Match All
=========

By default ``S()`` with no filters or queries specified will do a
``match_all`` query in ElasticSearch.

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

A query affects the score for a document. If you do a term query on
whether field `foo` has value `bar`, then the result set will score
documents where the query holds true higher than documents where the
query does not hold true.

The other place where this affects things is when you specify
facets. See :ref:`queries-chapter-facets-section` for details.


Queries
=======

The query is specified by keyword arguments to the ``query()``
method. The key of the keyword argument is parsed splitting on ``__``
(that's two underscores) with the first part as the "field" and the
second part as the "field action".

For example::

   q = S().query(title='taco trucks')


will do an elasticsearch term query for "taco trucks" in the title field.

And::

   q = S().query(title__text='taco trucks')


will do a text query instead of a term query.

There are many different field actions to choose from:

======================  ===================
field action            elasticsearch query
======================  ===================
(no action specified)   term query
term                    term query
text                    text query
prefix                  prefix query [1]_
gt, gte, lt, lte        range query
fuzzy                   fuzzy query
text_phrase             text_phrase query
query_string            query_string query [2]_
======================  ===================


.. [1] You can also use ``startswith``, but that's deprecated.

.. [2] When doing ``query_string`` queries, if the query text is malformed
   it'll raise a `SearchPhaseExecutionException:` exception.


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


Filters
=======

::

   q = (S().query(title='taco trucks')
           .filter(style='korean'))


will do a query for "taco trucks" in the title field and filter on the
style field for 'korean'. This is how we find Korean Taco Trucks.

As with ``query()``, ``filter()`` allow for you to specify field
actions for the filters:

================  ====================
field action      elasticsearch filter
================  ====================
in                Terms filter
gt, gte, lt, lte  Range filter
(no action)       Term filter
================  ====================


.. seealso::

   http://www.elasticsearch.org/guide/reference/query-dsl/
     ElasticSearch docs for query dsl

   http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
     ElasticSearch docs for terms filter

   http://www.elasticsearch.org/guide/reference/query-dsl/range-filter.html
     ElasticSearch docs for range filter

   http://www.elasticsearch.org/guide/reference/query-dsl/term-filter.html
     ElasticSearch docs for term filter


Advanced filters and F
======================

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
       ]},
    'fields': ['id']}


in elasticutils JSON.

You can do the same thing by putting both filters in the same
``.filter()`` call.

For example::

   q = S().filter(style='korean', price='FREE')


that also translates to::

   {'filter': {
       'and': [
           {'term': {'style': 'korean'}},
           {'term': {'price': 'FREE'}}
       ]},
    'fields': ['id']}


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
       ]},
    'fields': ['id']}


But, that's kind of icky looking.

So, we've also got an ``F`` class that makes this sort of thing
easier.

You can do the previous example with ``F`` like this::

   q = S().filter(F(style='korean') | F(style='mexican'))


will get you all the search results that are either "korean" or
"mexican" style.

That translates to::

   {'filter': {
       'or': [
           {'term': {'style': 'korean'}},
           {'term': {'style': 'mexican'}}
       ]},
    'fields': ['id']}


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
       ]},
    'fields': ['id']}


``F`` supports AND, OR, and NOT operators which are ``&``, ``|`` and
``~`` respectively.

Additionally, you can create an empty ``F`` and build it
incrementally::

    qs = S()
    f = F()
    if some_crazy_thing:
        f &= F(price='FREE')
    if some_other_crazy_thing:
        f |= F(style='mexican')

    qs = qs.filter(f)

If neither `some_crazy_thing` or `some_other_crazy_thing` are
``True``, then ``F`` will be empty. That's ok because empty filters
are ignored.


Query-time field boosting
=========================

ElasticSearch allows you to boost scores for fields specified in the
search query at query-time.

ElasticUtils allows you to specify query-time field boosts with
``.boost()``. It takes a set of arguments where the keys are either
field names or field name + '__' + field action.

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


Highlighting
============

ElasticUtils allows you to highlight excerpts that match the query
using the ``.highlight()`` transform. This returns data that will be
in every item in the search results list as ``_highlight``.

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

If you need to clear the highlight, call ``.highlight()`` with
``None``. For example, this search won't highlight anything::

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

Facets
======

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
     },
     'fields': ['id']}

Note that the fieldname you provide in the ``.facet()`` call becomes
the facet name as well.

The facet counts are available through ``.facet_counts()`` on the `S`
instance. For example::

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
     },
     'fields': ['id']}


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
     },
     'fields': ['id']}


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
     },
     'fields': ['id']}


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
             'terms': {'field': 'style'}},
         'location': {
             'global': True,
             'terms': {'field': 'location'}
         }
     },
     'fields': ['id']}

.. Note::

   The flag name is `global_` with an underscore at the end. Why?
   Because `global` with no underscore is a Python keyword.


.. seealso::

   http://www.elasticsearch.org/guide/reference/api/search/facets/
     ElasticSearch docs on facets, facet_filter, and global

   http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
     ElasticSearch docs on terms facet



Facets... RAW!
--------------

ElasticSearch facets can do a lot of other things. Because of this,
there exists ``.facet_raw()`` which will do whatever you need it to.
Specify key/value args by facet name.

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
     },
     'fields': ['id']}


.. Warning::

   If for some reason you have specified a facet with the same name
   using both ``.facet()`` and ``.facet_raw()``, the ``.facet_raw()``
   one will override the ``.facet()`` one.


.. seealso::

   http://www.elasticsearch.org/guide/reference/modules/scripting.html
     ElasticSearch docs on scripting


Counts
======

Total hits can be found by using ``.count()``. For example::

    q = S().query(title='taco trucks')
    count = q.count()


.. Note::

   Don't use Python's ``len`` built-in on the `S` instance if you want
   the number of documents in your index that matches your search.

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
   documents.



Results
=======

By default
----------

Results are lazy-loaded, so the query will not be made until you try
to access an item or some other attribute requiring the data.

If you have a typed `S` (e.g. ``S(Model)``), then by default, results
will be instances of that type.

If you have an untyped `S` (e.g. ``S()``), then by default, results
will be dicts.


Results as a list of tuples
---------------------------

`values_list` with no arguments returns a list of tuples each with an
id. With arguments, it'll return a list of tuples of values of the
fields specified in the order the fields were specified.

For example:

>>> list(S().values_list())
[(1,), (2,), (3,)]
>>> list(S().values_list('id', 'name'))
[(1, 'fred'), (2, 'brian'), (3, 'james')]
>>> list(S().values_list('name', 'id')
[('fred', 1), ('brian', 2), ('james', 3)]


Results as a list of dicts
--------------------------

`values_dict` returns a list of dicts. With no arguments, it returns a
list of dicts with a single ``id`` field. With arguments, it returns a
list of dicts with specified fields.

For example:

>>> list(S().values_dict())
[{'id': 1}, {'id': 2}]
>>> list(S().values_dict('id', 'name')
[{'id': 1, 'name': 'fred'}, {'id': 2, 'name': 'brian'}]


.. _scores-and-explanations:

Scores and explanations
=======================

Seeing the score
----------------

Wondering what the score for a document was? ElasticUtils puts that in
the ``_score`` on the search result. For example, let's search an
index that holds knowledge base articles for ones with the word
"crash" in them and print out the scores::

    q = S().query(title__text='crash', content__text='crash')

    for result in q:
        print result._score

This works regardless of what form the search results are in.


Getting an explanation
----------------------

Wondering why one document shows up higher in the results than another
that should have shown up higher? Wonder how that score was computed?
You can set the search to pass the ``explain`` flag to ElasticSearch
with the ``.explain()`` transform.

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
