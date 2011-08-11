.. _installation:

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

.. data:: ES_DUMP_CURL

    If set to a path all the requests that `ElasticUtils` makes will be dumped
    into the designated file.

    .. note:: Python does not write this file until the process is finished.


.. data:: ES_HOSTS

    This is a list of hosts.  In development this will look like::

        ES_HOSTS = ['127.0.0.1:9200']

.. data:: ES_INDEX

    This is the name of your primary ElasticSearch index.
