.. _mapping-type-chapter:

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

See :ref:`indexing-types-and-mappings` for documentation on defining
mappings in the index.

See :py:class:`elasticutils.MappingType` for documentation on creating
MappingTypes.
