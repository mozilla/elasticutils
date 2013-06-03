===========================
 Running and writing tests
===========================

Running the tests
=================

You can run the tests with::

    ./run_tests.py


This will run all the tests.


.. Note::

   If you need to adjust the settings, copy ``test_settings.py`` to a
   new file (like ``test_settings_local.py``), edit the file, and specify that
   as the value for the environment variable ``DJANGO_SETTINGS_MODULE``.

       DJANGO_SETTINGS_MODULE=test_settings_local ./run_tests.py

   This is helpful if you need to change the value of ``ES_HOSTS`` to
   match the ip address or port that elasticsearch is listening on.


Writing tests
=============

Tests are located in `elasticutils/tests/`.

We use `nose <https://github.com/nose-devs/nose>`_ for test utilities
and running tests.


ElasticTestCase
===============

If you're testing things in ElasticUtils that require hitting an
Elasticsearch cluster, then you should subclass
`elasticutils.tests.ESTestCase` which has code in it for making
things easier.

.. autoclass:: elasticutils.tests.ESTestCase
   :members:
