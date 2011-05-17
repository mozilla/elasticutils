.. ElasticUtils documentation master file, created by
   sphinx-quickstart on Mon May 16 15:52:49 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ElasticUtils
============

ElasticUtils makes querying and filtering and collecting facets from
ElasticSearch simple ::


    q = (S(product='firefox').filter(version='4.0', platform='all')
                             .facet('product', global_=True).facet('version')
                             .facet('platform').facet('type'))

Search All
----------

By default ``S()`` will do a ``match_all`` query in ElasticSearch.


Search Query
------------

``S('taco trucks')`` will do a query for "taco trucks".


Filters
-------

``S('taco trucks').filter(style='korean')`` will do a query for "taco trucks"
filtering on the attribute ``style``.  This is how we find Korean Taco Trucks.


Facets
------

``S('taco trucks').facet('style').facet('location')`` will do a query for
"taco trucks" and return facets for the ``style`` and ``location`` fields.
