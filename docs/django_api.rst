.. _django-api-docs-chapter:

=================
 Django API docs
=================

.. contents::
   :local:


The S class
===========

.. autoclass:: elasticutils.contrib.django.S
   :members:

   This shows the Django-specific documentation. See
   :py:class:`elasticutils.S` for more the rest.

   .. automethod:: elasticutils.contrib.django.S.__init__


The MappingType class
=====================

.. autoclass:: elasticutils.contrib.django.MappingType
   :members:

   This shows the Django-specific documentation. See
   :py:class:`elasticutils.MappingType` for more the rest.


The Indexable class
===================

.. autoclass:: elasticutils.contrib.django.Indexable
   :members:

   This shows the Django-specific documentation. See
   :py:class:`elasticutils.Indexable` for more the rest.



View decorators
===============

.. autofunction:: elasticutils.contrib.django.es_required

.. autofunction:: elasticutils.contrib.django.es_required_or_50x


The ESExceptionMiddleware class
===============================

.. autoclass:: elasticutils.contrib.django.ESExceptionMiddleware


Tasks
=====

.. automodule:: elasticutils.contrib.django.tasks

   .. autofunction:: index_objects(model, ids=[...])


The ESTestCase class
====================

Subclass this and make it do what you need it to do. It's definitely
worth reading the code.

.. autoclass:: elasticutils.contrib.django.estestcase.ESTestCase
   :members:
