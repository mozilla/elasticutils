============
Installation
============

`elasticutils` depends on the following settings:

.. module:: django.conf.settings

.. data:: ES_DISABLED

    `ES_DISABLED` disabled
    talking to ElasticSearch
    from your app.
    Any method
    wrapped with `es_required`
    will return and
    log a warning.
    This is useful
    while developing,
    so you don't have to
    have ElasticSearch running.

.. data:: ES_HOSTS

    This is a list of hosts.  In development this will look like::

        ES_HOSTS = ['127.0.0.1:9200']

.. data:: ES_INDEX

    This is the name of your primary ElasticSearch index.
