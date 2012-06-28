=========================
Running and writing tests
=========================

Running the tests
=================

If you don't have Django installed, you can run the tests with::

    nosetests

It will skip the Django tests.

If you do have Django installed, then you need to specify
``DJANGO_SETTINGS_MODULE``. Run the tests like this::

    DJANGO_SETTINGS_MODULE=test_settings nosetests


.. Note::

   If you need to adjust the settings, copy ``test_settings.py`` to a
   new file (like ``test_settings_local.py``), edit the file, and pass
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

If you're testing things in ElasticUtils that require hitting an
ElasticSearch instance, then you should subclass
`elasticutils.tests.ElasticTestCase` which has code in it for making
things easier.

.. autoclass:: elasticutils.tests.ElasticTestCase
   :members:
