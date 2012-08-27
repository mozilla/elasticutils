=========
Debugging
=========

Here are a few helpful utilities for debugging your ElasticUtils work.


Score explanations
==================

Want to see how a score for a search result was calculated? See
:ref:`scores-and-explanations`.


get_es dump_curl
================

You can pass a function into `get_es()` which will let you dump the
curl equivalents.

For example::

    from elasticutils import get_es

    class CurlDumper(object):
        def write(self, s):
            print s

    es = get_es(dump_curl=CurlDumper())


elasticsearch-head
==================

https://github.com/mobz/elasticsearch-head

elasticsearch-head is the phpmyadmin for elasticsearch. It makes it
much easier to see what's going on.


elasticsearch-paramedic
=======================

https://github.com/karmi/elasticsearch-paramedic

elasticsearch-paramedic allows you to see the state and real-time statistics
of your ES cluster.


ngrep
=====

http://ngrep.sourceforge.net/

Sometimes, it helps to see exactly what's going over the wire. ngrep has a
horrible web-site, but it's a super handy tool for seeing the complete
conversation. You can use it like this::

    $ ngrep -d any -p 9200

And then run your program and watch the output.

I often use this when testing sample ElasticUtils programs to see how
mappings, document values, facets, filters, queries and all that work.
