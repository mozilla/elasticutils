==========================
Querying with ElasticUtils
==========================

ElasticUtils makes querying and filtering and collecting facets from
ElasticSearch simple.

For example:

.. code-block:: python

   q = (S(model).query(title='Example')
                .filter(product='firefox')
                .filter(version='4.0', platform='all')
                .facet(products={'field':'product', 'global': True})
                .facet(versions={'field': 'version'})
                .facet(platforms={'field': 'platform'})
                .facet(types={'field': 'type'}))


Where ``model`` is a Django ORM model class.

Each call to ``query``, ``filter``, ``facet``, ``sort_by``, etc will
create a new S object with the accumulated search criteria.

.. Note::

   If you're not using Django, you can create stub-models. See the
   tests for more details.


Match All
=========

By default ``S(Model)`` will do a ``match_all`` query in ElasticSearch.


Search Query
============

The query is specified by keyword arguments to the ``query()``
method. The key of the keyword argument is parsed splitting on ``__``
(that's two underscores) with the first part as the "field" and the
second part as the "field action".

For example:

.. code-block:: python

   q = S(Model).query(title='taco trucks')


will do an elasticsearch term query for "taco trucks" in the title field.

And:

.. code-block:: python

   q = S(Model).query(title__text='taco trucks')


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

.. code-block:: python

   q = (S(Model).query(title='taco trucks')
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


Advanced filters
================

Calling filter multiple times is equivalent to an "and"ing of the
filters.

For example:

.. code-block:: python

   q = (S(Model).filter(style='korean')
                .filter(price='FREE'))

will do a query for style 'korean' AND price 'FREE'. Anything that has
a style other than 'korean' or a price other than 'FREE' is removed
from the result set.

This translates to:

.. code-block:: javascript

   {'filter': {
       'and': [
           {'term': {'style': 'korean'}},
           {'term': {'price': 'FREE'}}
       ]},
    'fields': ['id']}


in elasticutils JSON.

You can do the same thing by putting both filters in the same
``.filter()`` call.

For example:

.. code-block:: python

   q = S(Model).filter(style='korean', price='FREE')


that also translates to:

.. code-block:: javascript

   {'filter': {
       'and': [
           {'term': {'style': 'korean'}},
           {'term': {'price': 'FREE'}}
       ]},
    'fields': ['id']}


in elasticutils JSON.

Suppose you want either Korean or Mexican food. For that, you need an
"or".

You can do something like this:

.. code-block:: python

   q = S(Model).filter(or_={'style': 'korean', 'style'='mexican'})


That translates to:

.. code-block:: javascript

   {'filter': {
       'or': [
           {'term': {'style': 'korean'}},
           {'term': {'style': 'mexican'}}
       ]},
    'fields': ['id']}


But, that's kind of icky looking.

So, we've also got an ``F`` class that makes this sort of thing
easier.

You can do the previous example with ``F`` like this:

.. code-block:: python

   q = S(Model).filter(F(style='korean') | F(style='mexican'))


will get you all the search results that are either "korean" or
"mexican" style.

That translates to:

.. code-block:: javascript

   {'filter': {
       'or': [
           {'term': {'style': 'korean'}},
           {'term': {'style': 'mexican'}}
       ]},
    'fields': ['id']}


What if you want Mexican food, but only if it's FREE, otherwise you
want Korean?

.. code-block:: python

   q = S(Model).filter(F(style='mexican', price='FREE') | F(style='korean'))


That translates to:

.. code-block:: javascript
   
   {'filter': {
       'or': [
           {'and': [
               {'term': {'price': 'FREE'}},
               {'term': {'style': 'mexican'}}
           ]},
           {'term': {'style': 'korean'}}
       ]},
    'fields': ['id']}


``F`` supports AND, OR, and NOT operators.


Facets
======

.. code-block:: python

   q = (S(Model).query(title='taco trucks')
                .facet(styles={'field': 'style'},
                       locations={'field':'location'}))


will do a query for "taco trucks" and return facets for the ``style``
and ``location`` fields. The facets are available from the ``facets``
properties.

That translates to:

.. code-block:: javascript

   {'query': {
       'term': {'title': 'taco trucks'}},
       'facets': {
           'styles': {'field': 'style'},
           'locations': {'field': 'location'}
       },
    'fields': ['id']}


Facets can also be scripted_::

    S(Model).query(title='taco trucks').facet(styles={
        'field': 'style', 
        'script': 'term == korean ? true : false'
    })


.. Note::

   Unless the ``facet_filter`` property is specified on each facet,
   all the filters will be used for the facet_filter by default.


Counts
======

Total hits can be found by doing:

.. code-block:: python

    r = S(Model).query(title='taco trucks')
    r.count()
    len(r)


Results
=======

Results are lazy-loaded, so the query will not be made until you try
to access an item or some other attribute requiring the data.

By default, results will be returned as instances of the Model class
provided in the constructor. However, you can get the results back as
a list or dictionaries or tuples, if you'd rather:

>>> S(Model).query(type='taco trucks').values('title')
[(1, 'De La Tacos',), (2, 'Oriental Tacos',),]
>>> S(Model).query(type='taco trucks').values_dict('title')
[{'id': 1, 'title': 'De La Tacos'}, {'id': 2, 'title': 'Oriental Tacos'}]


Arguments passed to ``values`` or ``values_dict`` will select the
fields that are returned, including the ``id``.


.. _Text: http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
.. _Prefix: http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
.. _Range: http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
.. _Fuzzy: http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
.. _Term: http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html
.. _Terms: http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
.. _scripted: http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html

