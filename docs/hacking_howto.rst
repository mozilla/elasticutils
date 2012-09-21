.. _hacking-howto-chapter:

=============
Hacking HOWTO
=============

This covers setting up a development environment for developing on
ElasticUtils. If you're interested in using ElasticUtils, then you
should check out :ref:`users-guide`.


External requirements
=====================

You should have `elasticsearch <http://elasticsearch.org/>`_ installed
and running.


Get dependencies
================

Run::

    $ virtualenv ./venv/
    $ . ./venv/bin/activate
    $ pip install -r requirements-dev.txt

If you want to work on the contrib.django bits, you also need to do::

    $ pip install -r requirements-django.txt

This sets up all the required dependencies for development of ElasticUtils.

.. Note::

   You don't have to put your virtual environment in ``./venv/``. Feel
   free to put it anywhere.
