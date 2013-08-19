.. _hacking-howto-chapter:

===============
 Hacking HOWTO
===============

This covers setting up a development environment for developing on
ElasticUtils. If you're interested in using ElasticUtils, then you
should check out :ref:`users-guide`.


External requirements
=====================

You should have `Elasticsearch <http://elasticsearch.org/>`_ installed
and running.


Install dependencies
====================

Run::

    $ virtualenv ./venv
    $ . ./venv/bin/activate
    $ pip install -r requirements/dev.txt
    $ python setup.py develop


This sets up the required dependencies for development of ElasticUtils.

.. Note::

   You don't have to put your virtual environment in ``./venv/``. Feel
   free to put it anywhere.
