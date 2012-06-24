=================
Using with Django
=================

.. contents::
   :local:


Using with Django ORM models
============================

Django models and ElasticSearch indices make a natural fit. It would
be terribly useful if a Django model knew how to add and remove itself
from ElasticSearch. This is where the
:class:`elasticutils.models.SearchMixin` comes in.

You can then utilize things such as
:func:`~elasticutils.tasks.index_objects` to automatically index all
new items.

.. autoclass:: elasticutils.models.SearchMixin
   :members:

.. automodule:: elasticutils.tasks

   .. autofunction:: index_objects(model, ids=[...])

.. automodule:: elasticutils.cron

   .. autofunction:: reindex_objects(model, chunk_size[=150])


Writing tests
=============

Requires:

* `test_utils <https://github.com/jbalogh/test-utils>`_
* `nose <http://nose.readthedocs.org/en/latest/>`_

In `elasticutils.djangolib`, is `ESTestCase` which can be subclassed
in your app's test cases.

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
