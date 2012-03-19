=======
Testing
=======

Testing elasticutils things in your code
========================================

`ESTestCase` can be subclassed in your apps testcases.

It does the following:

* If `ES_HOSTS` is empty it raises a `SkipTest`.
* `self.es` is available from the `ESTestCase` class and any subclasses.
* At the end of the Test Case the index is destroyed.


Testing elasticutils itself
===========================

Testing elasticutils requires pyes_ and nose_. The easiest way to test is
to set up a new virtualenv with those packages installed::

    mkvirtualenv elasticutils
    workon elasticutils
    pip install -r requirements-extra.txt

Then from the elasticutils base directory run::

    DJANGO_SETTINGS_MODULE=es_settings nosetests -w tests

.. Note::

   If you need to adjust the settings, copy ``es_settings.py`` to a
   new file (like ``es_settings_local.py``), edit the file, and pass
   that in as the value for ``DJANGO_SETTINGS_MODULE``.

   This is helpful if you need to change the value of ``ES_HOSTS`` to
   match the ip address or port that elasticsearch is listening on.

.. _pyes: http://pypi.python.org/pypi/pyes/
.. _nose: http://somethingaboutorange.com/mrl/projects/nose/
