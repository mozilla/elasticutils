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

.. data:: ES_DUMP_CURL

   If set to a file path all the requests that `ElasticUtils` makes
   will be dumped into the designated file.

   If set to a class instance, calls the ``.write()`` method with
   the curl equivalents.

   See :ref:`django-debugging` for more details.

.. data:: ES_HOSTS

   This is a list of ES hosts. In development this will look like::

       ES_HOSTS = ['127.0.0.1:9200']

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

   Defines the timeout for the `ES` connection.  This defaults to 5
   seconds.


ES
==

The `get_es()` in the Django contrib will helpfully cache your ES
objects thread-local.

It is built with the settings from your `django.conf.settings`.

.. Note::

   `get_es()` only caches the `ES` if you don't pass in any override
   arguments. If you pass in override arguments, it doesn't cache it
   and instead creates a new one.


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
                # The id is an integer, so store it as such. ES would have
                # inferred this just fine.
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


Cron
----

.. automodule:: elasticutils.contrib.django.cron

   .. autofunction:: reindex_objects(model, chunk_size[=150])


Writing tests
=============

:Requirements: Django, test_utils, nose

In `elasticutils.contrib.django.estestcase`, is `ESTestCase` which can
be subclassed in your app's test cases.

It does the following:

* If `ES_HOSTS` is empty it raises a `SkipTest`.
* `self.es` is available from the `ESTestCase` class and any subclasses.
* At the end of the test case the index is wiped.

Example::

    from elasticutils.djangolib import ESTestCase


    class TestQueries(ESTestCase):
        def test_query(self):
            ...

        def test_locked_filters(self):
            ...


.. _django-debugging:

Debugging
=========

You can set the ``settings.ES_DUMP_CURL`` to a few different things
all of which can be helpful in debugging ElasticUtils.

1. a file path

   This will cause PyES to write the curl equivalents of the commands
   it's sending to ElasticSearch to a file.

   Example setting::

       ES_DUMP_CURL = '/var/log/es_curl.log'


   .. Note::

      The file is not closed until the process ends. Because of that,
      you don't see much in the file until it's done.


2. a class instance that has a ``.write()`` method

   PyES will call the ``.write()`` method with the curl equivalent and
   then you can do whatever you want with it.

   For example, this writes curl equivalent output to stdout::

        class CurlDumper(object):
            def write(self, s):
                print s
        ES_DUMP_CURL = CurlDumper()
