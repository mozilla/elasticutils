==============================================
elasticutils.contrib.django: Using with Django
==============================================

.. contents::
   :local:


Summary
=======

Django helpers are all located in `elasticutils.contrib.django`.

This chapter covers using ElasticUtils Django bits.


Configuration
=============

ElasticUtils depends on the following settings in your Django settings
file:

.. module:: django.conf.settings

.. data:: ES_DISABLED

   If `ES_DISABLED = True`, then Any method wrapped with
   `es_required` will return and log a warning. This is useful while
   developing, so you don't have to have ElasticSearch running.

.. data:: ES_URLS

   This is a list of ElasticSearch urls. In development this will look
   like::

       ES_URLS = ['http://localhost:9200']

.. data:: ES_INDEXES

   This is a mapping of doctypes to indexes. A `default` mapping is
   required for types that don't have a specific index.

   When ElasticUtils queries the index for a model, by default it
   derives the doctype from `Model._meta.db_table`. When you build
   your indexes and mapping types, make sure to match the indexes and
   mapping types you're using.

   Example 1::

       ES_INDEXES = {'default': 'main_index'}

   This only has a default, so all ElasticUtils queries will look in
   `main_index` for all mapping types.

   Example 2::

       ES_INDEXES = {'default': 'main_index',
                     'splugs': 'splugs_index'}

   Assuming you have a `Splug` model which has a
   `Splug._meta.db_table` value of `splugs`, then ElasticUtils will
   run queries for `Splug` in the `splugs_index`.  ElasticUtils will
   run queries for other models in `main_index` because that's the
   default.

   Example 3::

       ES_INDEXES = {'default': ['main_index'],
                     'splugs': ['splugs_index']}

   FIXME: The API allows for this. Pretty sure it should query
   multiple indexes, but we have no tests for that and I haven't
   tested it, either.


.. data:: ES_TIMEOUT

   Defines the timeout for the `ElasticSearch` connection.  This
   defaults to 5 seconds.


ElasticSearch
=============

The `get_es()` in the Django contrib will use Django settings listed
above to build the ElasticSearch object.


Using with Django ORM models
============================

:Requirements: Django

The `elasticutils.contrib.django.S` class takes a `MappingType` in the
constructor. That allows you to tie Django ORM models to ElasticSearch
index search results.

In ``elasticutils.contrib.django.models`` is `DjangoMappingType` which
has some additional Django ORM-specific code in it to make it easier.

Define a `DjangoMappingType` subclass for your model. The minimal you
need to define is `get_model`.

Further, you can use the `Indexable` mixin to get a bunch of helpful
indexing-related code.

For example, here's a minimal `DjangoMappingType` subclass::

    from django.models import Model
    from elasticutils.contrib.django.models import DjangoMappingType


    class MyModel(Model):
        ...


    class MyMappingType(DjangoMappingType):
        @classmethod
        def get_model(cls):
            return MyModel

    searcher = MyMappingType.search()


Here's one that uses `Indexable` and handles indexing::

    from django.models import Model
    from elasticutils.contrib.django.models import DjangoMappingType


    class MyModel(Model):
        ...


    class MyMappingType(DjangoMappingType, Indexable):
        @classmethod
        def get_model(cls):
            return MyModel

        @classmethod
        def extract_document(cls, obj_id, obj=None):
            if obj is None:
                obj = cls.get_model().get(pk=obj_id)

            return {
                'id': obj.id,
                'name': obj.name,
                'bio': obj.bio,
                'age': obj.age
                }


    searcher = MyMappingType.search()


This example doesn't specify a mapping. That's ok because
ElasticSearch will infer from the shape of the data how it should
analyze and store the data.

If you want to specify this explicitly (and I suggest you do for
anything that involves strings), then you want to additionally
override `.get_mapping()`. Let's refine the above example by
explicitly specifying `.get_mapping()`.

::

    from django.models import Model
    from elasticutils.contrib.django.models import DjangoMappingType


    class MyModel(Model):
        ...


    class MyMappingType(DjangoMappingType, Indexable):
        @classmethod
        def get_model(cls):
            return MyModel

        @classmethod
        def get_mapping(cls):
            """Returns an ElasticSearch mapping."""
            return {
                # The id is an integer, so store it as such. ElasticSearch
                # would have inferred this just fine.
                'id': {'type': 'integer'},

                # The name is a name---so we shouldn't analyze it
                # (de-stem, tokenize, parse, etc).
                'name': {'type': 'string', 'index': 'not_analyzed'},

                # The bio has free-form text in it, so analyze it with
                # snowball.
                'bio': {'type': 'string', 'analyzer': 'snowball'},

                # Age is an integer
                'age': {'type': 'integer'}
                }

        @classmethod
        def extract_document(cls, obj_id, obj=None):
            if obj is None:
                obj = cls.get_model().get(pk=obj_id)

            return {
                'id': obj.id,
                'name': obj.name,
                'bio': obj.bio,
                'age': obj.age
                }


    searcher = MyMappingType.search()



DjangoMappingType
-----------------

.. autoclass:: elasticutils.contrib.django.models.DjangoMappingType
   :members:


Indexable
---------

.. autoclass:: elasticutils.contrib.django.models.Indexable
   :members:


.. seealso::

   http://www.elasticsearch.org/guide/reference/mapping/
     The ElasticSearch guide on mapping types.

   http://www.elasticsearch.org/guide/reference/mapping/core-types.html
     The ElasticSearch guide on mapping type field types.


Other helpers
=============

:Requirements: Django, Celery

You can then utilize things such as
:func:`elasticutils.contrib.django.tasks.index_objects` to
automatically index all new items.


View decorators
---------------

.. autofunction:: elasticutils.contrib.django.es_required

.. autofunction:: elasticutils.contrib.django.es_required_or_50x


Tasks
-----

.. automodule:: elasticutils.contrib.django.tasks

   .. autofunction:: index_objects(model, ids=[...])


Writing tests
=============

:Requirements: Django

When writing test cases for your ElasticUtils-using code, you'll want
to do a few things:

1. Default ``ES_DISABLED`` to `True`. This way, the tests that kick off
   creating data but aren't testing search-specific things don't
   additionally index stuff. That'll save you a bunch of test time.

2. When testing ElasticUtils things, override the settings and set
   ``ES_DISABLED`` to `False`.

3. Use an ``ESTestCase`` that sets up the indexes before tests run and
   tears them down after they run.

4. When testing, make sure you use an index name that's unique. You
   don't want to run your tests and have them affect your production
   index.

You can use
:py:class:`elasticutils.contrib.django.estestcase.ESTestCase`
for your app's tests. It's pretty basic but does all of the above
except item 1 which you'll need to do in your test settings.

Example usage::

    from elasticutils.contrib.django.estestcase import ESTestCase 


    class TestQueries(ESTestCase):
        # This class holds tests that do elasticsearch things

        def test_query(self):
            ...

        def test_locked_filters(self):
            ...


ElasticUtils uses this for it's Django tests. Look at the test code
for more examples of usage:

https://github.com/mozilla/elasticutils/

If it's not what you want, you could subclass it and override behavior
or just write your own.


The ESTestCase class
--------------------

Subclass this and make it do what you need it to do. It's definitely
worth reading the code.

.. autoclass:: elasticutils.contrib.django.estestcase.ESTestCase
   :members:
