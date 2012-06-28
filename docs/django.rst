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

ElasticUtils depends on the following settings:

.. module:: django.conf.settings

.. data:: ES_DISABLED

    Disables talking to ElasticSearch from your app.  Any method
    wrapped with `es_required` will return and log a warning.  This is
    useful while developing, so you don't have to have ElasticSearch
    running.

.. data:: ES_DUMP_CURL

    If set to a path all the requests that `ElasticUtils` makes will
    be dumped into the designated file.

    .. note:: Python does not write this file until the process is
              finished.


.. data:: ES_HOSTS

    This is a list of hosts.  In development this will look like::

        ES_HOSTS = ['127.0.0.1:9200']

.. data:: ES_INDEXES

    This is a mapping of doctypes to indexes. A `default` mapping is
    required for types that don't have a specific index.

    When ElasticUtils queries the index for a model, it derives the
    doctype from `Model._meta.db_table`.  When you build your indexes
    and doctypes, make sure to name them after your model db_table.

    Example 1::

        ES_INDEXES = {'default': 'main_index'}

    This only has a default, so ElasticUtils queries will look in
    `main_index` for all doctypes.

    Example 2::

        ES_INDEXES = {'default': 'main_index',
                      'splugs': 'splugs_index'}

    Assuming you have a `Splug` model which has a
    `Splug._meta.db_table` value of `splugs`, then ElasticUtils will
    run queries for `Splug` in the `splugs_index`.  ElasticUtils will
    run queries for other models in `main_index` because that's the
    default.

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
   arguments. If you pass in override arguments, it doesn't cache it,
   but instead creates a new one.


Using with Django ORM models
============================

:Requirements: Django

The `elasticutils.contrib.django.S` class takes a model in the
constructor. That model is a Django ORM Models derivative. For example::

    from elasticutils.contrib.django import S
    from myapp.models import MyModel

    searcher = S(MyModel)

Further, you can have your model extend
:class:`elasticutils.contrib.django.models.SearchMixin` and get a
bunch of functionality that makes indexing data easier.

Two things to know:

1. The doctype for the model is ``cls._meta.db_table``.

2. The index that's searched is ``settings.ES_INDEXES[doctype]`` and
   if that doesn't exist, it defaults to
   ``settings.ES_INDEXES['default']``

.. autoclass:: elasticutils.contrib.django.models.SearchMixin
   :members:


Other helpers
=============

:Requirements: Django, Celery

You can then utilize things such as
:func:`~elasticutils.contrib.django.tasks.index_objects` to
automatically index all new items.

.. automodule:: elasticutils.contrib.django.tasks

   .. autofunction:: index_objects(model, ids=[...])

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


Debugging
=========

From Rob Hudson (with some minor editing):

    I recently discovered a nice tool for helping solve ElasticSearch
    problems that I thought I'd share...

    While scanning the code of pyes I discovered that it has an option
    to dump the commands it is sending to the ES backend to whatever
    you give it that has a ``write()`` method [1]_.  I also discovered
    that elasticutils will pass this through to pyes based on the
    ``settings.ES_DUMP_CURL`` [2]_.

    I threw together a quick and ugly class just to dump output while
    debugging an ES problem::

        class CurlDumper(object):
            def write(self, s):
                print s
        ES_DUMP_CURL = CurlDumper()

    This is pretty great when running a test with output enabled, or
    even in the runserver output. But to my surprise, when running
    tests with output not enabled I see the curl dump for only tests
    that fail, which has turned out to be very useful information.

.. [1] https://github.com/aparo/pyes/blob/master/pyes/es.py#L496
.. [2] https://github.com/mozilla/elasticutils/blob/master/elasticutils/__init__.py#L29
