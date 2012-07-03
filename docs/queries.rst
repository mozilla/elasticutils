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

================  ===================
field action      elasticsearch query
================  ===================
text              Text_ query
startswith        Prefix_ query
gt, gte, lt, lte  Range_ query
fuzzy             Fuzzy_ query
(no action)       Term_ query
================  ===================


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
in                Terms_ filter
gt, gte, lt, lte  Range_ filter
(no action)       Term_ filter
================  ====================

See the `elasticsearch docs on queries and filters
<http://www.elasticsearch.org/guide/reference/query-dsl/>`_.


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

To get the facet counts, you call ``.facet_counts()`` on the `S`
instance::

    counts = q.facet_counts()


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


Counts
======

Total hits can be found by doing::

    r = S().query(title='taco trucks')
    r.count()
    len(r)


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


.. _Text: http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
.. _Prefix: http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
.. _Range: http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
.. _Fuzzy: http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
.. _Term: http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html
.. _Terms: http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
.. _scripted: http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html

