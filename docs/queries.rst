==========================
Querying with ElasticUtils
==========================

ElasticUtils makes querying and filtering and collecting facets from
ElasticSearch simple ::


    q = (S(model).query(title='Example')
                 .filter(product='firefox')
                 .filter(version='4.0', platform='all')
                 .facet(products={'field':'product', 'global': True})
                 .facet(versions={'field': 'version'})
                 .facet(platforms={'field': 'platform'})
                 .facet(types={'field': 'type'}))


Where ``model`` is a Django-model class.

.. note::

    If you're not using Django,  you can create stub-models.  See the tests for
    more details.

Search All
----------

By default ``S(Model)`` will do a ``match_all`` query in ElasticSearch.


Search Query
------------

``S(Model).query(title='taco trucks')`` will do a term query for "taco trucks" 
in the title.

The query parameters can define different kinds of queries to do, for
example: ``S(Model).query(title__text='taco trucks')`` will do a text
query instead of a term query.

* ``title__text``: a Text_ query
* ``title__startswith``: a Prefix_ query
* ``title__gt``: a Range_ query (includes ``gt``, ``gte``, ``lt``, ``lte``)
* ``title__fuzzy``: a Fuzzy_ query
* ``title``: or no query type, will do a Term_ query

.. _Text: http://www.elasticsearch.org/guide/reference/query-dsl/text-query.html
.. _Prefix: http://www.elasticsearch.org/guide/reference/query-dsl/prefix-query.html
.. _Range: http://www.elasticsearch.org/guide/reference/query-dsl/range-query.html
.. _Fuzzy: http://www.elasticsearch.org/guide/reference/query-dsl/fuzzy-query.html
.. _Term: http://www.elasticsearch.org/guide/reference/query-dsl/term-query.html

Filters
-------

``S(Model).query(title='taco trucks').filter(style='korean')`` will do a query 
for "taco trucks" filtering on the attribute ``style``.  This is how we find 
Korean Taco Trucks.

.. note:: 
    Each call to ``query``, ``filter``, ``facet``, or ``sort_by`` will
    create new S objects, with the results combined.

As with Queries, Filters allow for you to specify the kind of filter to
do.

* ``style__in=['korean', 'mexican']``: a Terms_ filter
* ``style__gt``: a Range_ filter ((includes ``gt``, ``gte``, ``lt``, ``lte``)
* ``style``: or no filter type, will do a Term_ filter

.. _Terms: http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html
.. _Range: http://www.elasticsearch.org/guide/reference/query-dsl/range-filter.html
.. _Term: http://www.elasticsearch.org/guide/reference/query-dsl/term-filter.html


Multiple Filters
~~~~~~~~~~~~~~~~

``S(Model).query(title='taco trucks').filter(style='korean', price='FREE')``
will do a query for "taco trucks" that are "korean" style and have a price of
"FREE".


Complicated Filtering
~~~~~~~~~~~~~~~~~~~~~

Sometimes you want something complicated.  For that we have the ``F`` (filter)
object.

``S(Model).query(title='taco trucks').filter(F(style='korean')|F(style='thai'))``
will find you "thai" or "korean" style taco trucks.

Let's say you only want "korean" tacos if you can get it for "FREE" or "thai"
tacos at any price::

    S('taco trucks').filter(F(style='korean', price='FREE')|F(style='thai'))

.. note::
    ``F`` objects support AND, OR, and NOT operators.


Facets
------

``S(Model).query(title='taco trucks').facet(styles={'field': 'style'},
locations={'field':'location'})`` will do a query for "taco trucks" and return
facets for the ``style`` and ``location`` fields. The facets are
available from the ``facets`` properties.

Facets can also be scripted_::

    S(Model).query(title='taco trucks').facet(styles={
        'field': 'style', 
        'script': 'term == korean ? true : false'
    })

.. note:: 
    Unless the ``facet_filter`` property is specified on each facet,
    all the filters will be used for the facet_filter by default.

.. _scripted: http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html


Results
-------

Results are lazy-loaded, so the query will not be made until you try to
access an item or some other attribute requiring the data.

Total hits can be found by doing::

    r = S(Model).query(title='taco trucks')
    r.count()
    # or
    len(r)

Results-types
------------

By default, results will be returned as instances of the Model class
provided in the constructor. However, you can get the results back as a
list or dictionaries or tuples, if you'd rather::

    S(Model).query(type='taco trucks').values('title')
    > [(1, 'De La Tacos',), (2, 'Oriental Tacos',),]

    S(Model).quey(type='taco trucks').values_dict('title')
    > [{'id': 1, 'title': 'De La Tacos'}, {'id': 2, 'title': 'Oriental
        Tacos'}]

Arguments passed to ``values`` or ``values_dict`` will select the fields
that are returned, including the ``id``.

