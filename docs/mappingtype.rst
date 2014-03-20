.. _mapping-type-chapter:

==============================
 Mapping types and Indexables
==============================

The MappingType class
=====================

:py:class:`elasticutils.MappingType` lets you centralize concerns
regarding documents you're storing in your Elasticsearch index.


Lets you tie business logic to search results
---------------------------------------------

When you do searches with MappingTypes, you get back those results as
an iterable of MappingTypes by default.

For example, say you had a description field and wanted to have a
truncated version of it. You could do it this way:

.. code-block:: python

    class MyMappingType(MappingType):

        # ... missing code here

        def description_truncated(self):
            return self.description[:100]

    results = S(MyMappingType).query(description__text='stormy night')

    print list(results)[0].description_truncated()


Lets you link source data to search results
-------------------------------------------

You can relate a MappingType to a database model or other source
allowing you to link documents in the Elasticsearch index back to
their origins in a lazy-loading way. This is done by subclassing
MappingType and implementing the ``get_object()`` method. You can then
access the original data using the ``object`` property.

For example:

.. code-block:: python

    class MyMappingType(MappingType):

        # ... missing code here

        def get_object(self):
            return self.get_model().objects.get(pk=self._id)

    results = S(MyMappingType).filter(height__gte=72)[:1]

    first = list(results)[0]

    # This prints "height" which comes from the Elasticsearch
    # document
    print first.height

    # This prints "height" which comes from the database data
    # that the Elasticsearch document is based on. This is the
    # first time ``.object`` is used, so it does the db hit
    # here.
    print first.object.height


DefaultMappingType
------------------

The most basic MappingType is the DefaultMappingType which is returned
if you don't specify a MappingType and also don't call
:py:meth:`elasticutils.S.values_dict` or
:py:meth:`elasticutils.S.values_list`. The DefaultMappingType lets
you access search result fields as instance attributes or as keys:

.. code-block:: python

    res.description
    res['description']


The latter syntax is helpful when there are attributes defined on the
class that have the same name as the document field or aren't valid
Python names.


For more information
--------------------

See :ref:`indexing-types-and-mappings` for documentation on defining
mappings in the index.

See :py:class:`elasticutils.MappingType` for documentation on creating
MappingTypes.


The Indexable class
===================

:py:class:`elasticutils.Indexable` is a mixin for
:py:class:`elasticutils.MappingType` that has methods and classmethods
for making indexing easier.


Example
=======

Here's an example of a class that subclasses `MappingType` and
`Indexable`. It's based on a model called `BlogEntry`.

.. code-block:: python

    class BlogEntryMappingType(MappingType, Indexable):
        @classmethod
        def get_index(cls):
            return 'blog-index'

        @classmethod
        def get_mapping_type_name(cls):
            return 'blog-entry'

        @classmethod
        def get_model(cls):
            return BlogEntry

        @classmethod
        def get_es(cls):
            return get_es(urls=['http://localhost:9200'])

        @classmethod
        def get_mapping(cls):
            return {
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'tags': {'type': 'string'}
                }
            }

        @classmethod
        def extract_document(cls, obj_id, obj=None):
            if obj == None:
                obj = cls.get_model().get(id=obj_id)

            doc = {}
            doc['id'] = obj.id
            doc['title'] = obj.title
            doc['tags'] = obj.tags
            return doc

        @classmethod
        def get_indexable(cls):
            return cls.get_model().get_objects()


With this, I can write code elsewhere in my project that:

1. gets the mapping type name and mapping for documents of type
   "blog-entry"
2. gets all the objects that are indexable
3. for each object, extracts the Elasticsearch document data and
   indexes it

When I create my :py:class:`elasticutils.S` object, I'd create it like
this::

    s = S(BlogEntryMappingType)


and now by default any search results I get back are instances of the
`BlogEntryMappingType` class.
