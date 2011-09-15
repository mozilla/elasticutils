=======
Testing
=======

`ESTestCase` can be subclassed in your apps testcases.

It does the following:

* If `ES_HOSTS` is empty it raises a `SkipTest`.
* `self.es` is available from the `ESTestCase` class and any subclasses.
* At the end of the Test Case the index is destroyed.


Testing Elasticutils
--------------------

Testing elasticutils requires pyes_ and nose_. The easiest way to test is
to set up a new virtualenv with those packages installed::

    mkvirtualenv elasticutils
    workon elasticutils
    pip install pyes
    pip install nose

Then, ``cd`` to the elasticutils base directory and run::

    nosetests -w tests/

You may need to edit `es_settings.py` to change the value of ES_HOSTS to match
the IP or port that elasticsearch is listening on.

.. _pyes: http://pypi.python.org/pypi/pyes/

.. _nose: http://somethingaboutorange.com/mrl/projects/nose/
