.. _project-details:

==============
 ElasticUtils
==============

:Version:       |release|
:Code:          https://github.com/mozilla/elasticutils
:License:       BSD; see LICENSE file
:Issues:        https://github.com/mozilla/elasticutils/issues
:Documentation: http://elasticutils.readthedocs.org/
:IRC:           #elasticutils on irc.mozilla.org


ElasticUtils is a Python library that gives you a chainable search API
for `Elasticsearch <http://elasticsearch.org/>`_ as well as some other
tools to make it easier to integrate Elasticsearch into your
application.

So what's it like? Let's do a couple basic things:

Create an instance of :py:class:`elasticutils.S` and tell it which
index and doctype to look at.

>>> from elasticutils import S, F
>>> s = S().indexes('blog-index').doctypes('blog-entry')

Print the count of everything in that index with that type:

>>> s.count()
4

Show titles of all blog entries with "elasticutils" in the title:

>>> s = s.query(title__match='elasticutils')
>>> [result['title'] for result in s]
[u'ElasticUtils v0.4 released!', u'elasticutils status -- May 18th, 2012',
u'ElasticUtils sprint at PyCon US 2013']

You can also use properties rather than keys:

>>> [result.title for result in s]
[u'ElasticUtils v0.4 released!', u'elasticutils status -- May 18th, 2012',
u'ElasticUtils sprint at PyCon US 2013']

Filter out entries related to PyCon:

>>> s = s.filter(~F(tag='pycon'))
>>> [result['title'] for result in s]
[u'ElasticUtils v0.4 released!', u'elasticutils status -- May 18th, 2012']

Show only the top result:

>>> s = s[:1]
>>> [result['title'] for result in s]
[u'ElasticUtils v0.4 released!']

That's the gist of it!


Project
=======

.. toctree::
   :maxdepth: 1

   changelog
   theory
   resources


.. _users-guide:

User's Guide
============

.. toctree::
   :maxdepth: 1

   installation
   indexing
   mappingtype
   searching
   mlt
   debugging
   api


Using ElasticUtils with Django
==============================

.. toctree::
   :maxdepth: 1

   django
   django_api


Contributor's Guide
===================

.. toctree::
   :maxdepth: 1

   join
   hacking_howto
   dev_conventions
   dev_documentation
   dev_testing
   dev_releaseprocess


Sample programs
===============

.. toctree::
   :maxdepth: 1

   sampleprogram
   sampleprogramfacets


Indices and tables
==================

* :ref:`genindex`
