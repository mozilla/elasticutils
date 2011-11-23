.. _installation:

============
Installation
============

Download
--------

Clone it from https://github.com/davedash/elasticutils .


Configure
---------

`elasticutils` depends on the following settings:

.. module:: django.conf.settings

.. data:: ES_DISABLED

    Disables talking to ElasticSearch from your app.  Any method
    wrapped with `es_required` will return and log a warning.  This is
    useful while developing, so you don't have to have ElasticSearch
    running.

.. data:: ES_TIMEOUT

    Defines the timeout for the `ES` connection.  This defaults to 1 second.

.. data:: ES_DUMP_CURL

    If set to a path all the requests that `ElasticUtils` makes will be dumped
    into the designated file.

    .. note:: Python does not write this file until the process is finished.


.. data:: ES_HOSTS

    This is a list of hosts.  In development this will look like::

        ES_HOSTS = ['127.0.0.1:9200']

.. data:: ES_INDEXES

    This is a mapping of doctypes to indexes. A `default` mapping is required
    for types that don't have a specific index.

    When ElasticUtils queries the index for a model, it derives the doctype
    from `Model._meta.db_table`.  When you build your indexes and doctypes,
    make sure to name them after your model db_table.

    Example 1::

        ES_INDEXES = {'default': 'main_index'}

    This only has a default, so ElasticUtils queries will look in `main_index`
    for all doctypes.

    Example 2::

        ES_INDEXES = {'default': 'main_index',
                      'splugs': 'splugs_index'}

    Assuming you have a `Splug` model which has a `Splug._meta.db_table`
    value of `splugs`, then ElasticUtils will run queries for `Splug` in
    the `splugs_index`.  ElasticUtils will run queries for other models in
    `main_index` because that's the default.
