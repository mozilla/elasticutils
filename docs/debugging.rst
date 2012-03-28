=========
Debugging
=========

elasticsearch-head
==================

https://github.com/mobz/elasticsearch-head

elasticsearch-head is the phpmyadmin for elasticsearch. It makes it
much easier to see what's going on.


ES_DUMP_CURL
============

From Rob Hudson (with some minor editing):

    I recently discovered a nice tool for helping solve ElasticSearch
    problems that I thought I'd share...

    While scanning the code of pyes I discovered that it has an option
    to dump the commands it is sending to the ES backend to whatever
    you give it that has a ``write()`` method [1]_.  I also discovered
    that elasticutils will pass this through to pyes based on the
    ``settings.ES_DUMP_CURL`` [2]_.

    I threw together a quick and ugly class just to dump output while
    debugging an ES problem::

        class CurlDumper(object):
            def write(self, s):
                print s
        ES_DUMP_CURL = CurlDumper()

    This is pretty great when running a test with output enabled, or
    even in the runserver output. But to my surprise, when running
    tests with output not enabled I see the curl dump for only tests
    that fail, which has turned out to be very useful information.

.. [1] https://github.com/aparo/pyes/blob/master/pyes/es.py#L496
.. [2] https://github.com/mozilla/elasticutils/blob/master/elasticutils/__init__.py#L29
