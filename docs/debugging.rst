.. _debugging-chapter:

=========
Debugging
=========

Here are a few helpful utilities for debugging your ElasticUtils work.


Score explanations
==================

Want to see how a score for a search result was calculated? See
:ref:`scores-and-explanations`.


Logging
=======

pyelasticsearch logs to the ``pyelasticsearch`` logger using the
Python logging module. If you configure that to show DEBUG-level
messages, then it'll show the requests in curl form, responses, and
when it marks servers as dead.

Additionally, pyelasticsearch uses Requests which logs to the
``requests`` logger using the Python logging module. If you configure
that to show INFO-level messages, then you'll see all that stuff.

::

    import logging

    logging.getLogger('pyelasticsearch').setLevel(logging.DEBUG)
    logging.getLogger('requests').setLevel(logging.DEBUG)


.. Note::

   This assumes that logging is already set up with something like
   this::

       import logging

       logging.basicConfig()


pyelasticsearch will log lines like::

    DEBUG:pyelasticsearch:Making a request equivalent to this: curl
    -XGET 'http://localhost:9200/fooindex/testdoc/_search' -d '{"fa
    cets": {"topics": {"terms": {"field": "topics"}}}}'


You can copy and paste the curl line and it'll work on the command
line.

.. Note::

   If you add a ``pretty=1`` to the query string of the url that
   you're curling, then ElasticSearch will return a prettified
   response that's easier to read.


Seeing the query
================

The `S` class has a `_build_query()` method that you can use to see the
body of the ElasticSearch request it's generated with the parameters
you've specified so far. This is helpful in debugging ElasticUtils and
figuring out whether it's doing things poorly.

For example::

    some_s = S()
    print some_s._build_query()


.. Note::

   This is a "private" method, so we might change it at some point.
   Having said that, it hasn't changed so far and is probably useful
   for debugging.


elasticsearch-head
==================

https://github.com/mobz/elasticsearch-head

elasticsearch-head is the phpmyadmin for elasticsearch. It makes it
much easier to see what's going on.


elasticsearch-paramedic
=======================

https://github.com/karmi/elasticsearch-paramedic

elasticsearch-paramedic allows you to see the state and real-time
statistics of your ElasticSearch cluster.
