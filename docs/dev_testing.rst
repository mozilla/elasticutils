=========================
Running and writing tests
=========================

Running the tests
=================

To run the tests, do::

    DJANGO_SETTINGS_MODULE=es_settings nosetests


.. Note::

   If you need to adjust the settings, copy ``es_settings.py`` to a
   new file (like ``es_settings_local.py``), edit the file, and pass
   that in as the value for ``DJANGO_SETTINGS_MODULE``.

   This is helpful if you need to change the value of ``ES_HOSTS`` to
   match the ip address or port that elasticsearch is listening on.


Writing tests
=============

Tests are located in `elasticutils/tests/`.

We use `nose <https://github.com/nose-devs/nose>`_ for test utilities
and running tests.


ElasticTestCase
===============

If you're testing things that require hitting an ElasticSearch
instance, then you should subclass
`elasticutils.tests.ElasticTestCase` which has code in it for making
things easier.

.. autoclass:: elasticutils.tests.ElasticTestCase
   :members:
