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

   .. automethod:: elasticutils.contrib.django.S.__init__


The DjangoMappingType class
===========================

.. autoclass:: elasticutils.contrib.django.models.DjangoMappingType
   :members:


The Indexable class
===================

.. autoclass:: elasticutils.contrib.django.models.Indexable
   :members:


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
