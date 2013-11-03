.. _debugging-chapter:

===========
 Debugging
===========

Here are a few helpful utilities for debugging your ElasticUtils work.


Score explanations
==================

Want to see how a score for a search result was calculated? See
:ref:`scores-and-explanations`.


Logging
=======

elasticsearch-py logs to the ``elasticsearch`` and ``elasticsearch.trace``
loggers using the Python logging module.

If you configure ``elasticsearch.trace`` to show INFO-level messages, then
it'll show the requests in curl form, responses if you enable DEBUG.

``elasticsearch`` logger will give you information about node failures
(WARNING-level), their resurrection (INFO) and every request in a short form
(DEBUG). Additionally it will log a WARNING for any failed request.

Elasticsearch-py uses urllib3 by default which logs to the ``urllib3`` logger
using the Python logging module. If you configure that to show INFO-level
messages, then you'll see all that stuff. If you configured your
elasticsearch-py client to use other transport use it's logging capabilities.

First set up logging using something like this:

.. code-block:: python

    import logging

    # Set up the logging in some way. If you don't have logging
    # set up, you can set it up like this.
    logging.basicConfig()


Then set the logging level for the elasticsearch-py and urllib3 loggers
to ``logging.DEBUG``:

.. code-block:: python

    logging.getLogger('elasticsearch').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.DEBUG)


elasticsearch-py will log lines like::

    INFO:elasticsearch:GET http://localhost:9200/_search [status:200
    request:0.001s]


Or you can enable the ``elasticsearch.trace`` logger and have it log a shell
transcript of your session using curl:

.. code-block:: python

    tracer = logging.getLogger('elasticsearch.trace')
    tracer.setLevel(logging.DEBUG)
    tracer.addHandler(logging.FileHandler('/tmp/elasticsearch-py.sh'))


.. Note::

   The trace logger will always point to localhost:9200 and add ``?pretty`` to
   the query string of the url so that you're curling, then Elasticsearch will
   return a prettified response that's easier to read.


Seeing the query
================

The `S` class has a `_build_query()` method that you can use to see the
body of the Elasticsearch request it's generated with the parameters
you've specified so far. This is helpful in debugging ElasticUtils and
figuring out whether it's doing things poorly.

For example::

    some_s = S()
    print some_s._build_query()


.. Note::

   This is a "private" method, so we might change it at some point.
   Having said that, it hasn't changed so far and it is super helpful.


elasticsearch-head
==================

https://github.com/mobz/elasticsearch-head

elasticsearch-head is the phpmyadmin for elasticsearch. It makes it
much easier to see what's going on.


elasticsearch-paramedic
=======================

https://github.com/karmi/elasticsearch-paramedic

elasticsearch-paramedic allows you to see the state and real-time
statistics of your Elasticsearch cluster.


es2unix
=======

https://github.com/elasticsearch/es2unix

Use this for calling Elasticsearch API things instead of curl.
