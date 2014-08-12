
============================================================
 Migrating from Elasticsearch 0.90 to 1.0 with ElasticUtils
============================================================

.. Note::

   This is a work in progress and probably doesn't cover everything.


Summary
=======

There are a bunch of API-breaking changes between Elasticsearch 0.90
and 1.0. Because of this, it's really tricky to get over this hump 
without having downtime.

This document covers a high-level walk through for upgrading from
Elasticsearch 0.90 to 1.0 and the steps you should take to reduce
your downtime.


Resources
=========

.. seealso::

   http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/breaking-changes.html
     Breaking changes when migrating to Elasticsearch 1.0

   http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/_deprecations.html
     Deprecated features when migrating to Elasticsearch 1.0


Steps
=====

1. Upgrade to ElasticUtils 0.9.1

   This includes the elasticsearch-py library version 0.4.5--don't use
   a later version!

2. Upgrade your cluster to Elasticsearch 0.90.13

3. Upgrade to ElasticUtils 0.10

   Continue using elasticsearch-py 0.4.5.

4. Make any changes to your code so that it works with both Elasticsearch
   0.90 and 1.0

5. Upgrade to Elasticsearch 1.0.3

6. (Not implemented, yet) Upgrade to ElasticUtils 0.11

   This will use a more recent version of elasticsearch-py to be determined.


At that point, you should be fine.
