.. _api-docs-chapter:

==========
 API docs
==========

.. contents::
   :local:


Functions
=========

.. autofunction:: elasticutils.get_es


The S class
===========

.. autoclass:: elasticutils.S

   .. automethod:: elasticutils.S.__init__

   **Chaining transforms**

       .. automethod:: elasticutils.S.query

       .. automethod:: elasticutils.S.query_raw

       .. automethod:: elasticutils.S.filter

       .. automethod:: elasticutils.S.filter_raw

       .. automethod:: elasticutils.S.order_by

       .. automethod:: elasticutils.S.boost

       .. automethod:: elasticutils.S.demote

       .. automethod:: elasticutils.S.facet

       .. automethod:: elasticutils.S.facet_raw

       .. automethod:: elasticutils.S.highlight

       .. automethod:: elasticutils.S.search_type

       .. automethod:: elasticutils.S.suggest

       .. automethod:: elasticutils.S.values_list

       .. automethod:: elasticutils.S.values_dict

       .. automethod:: elasticutils.S.es

       .. automethod:: elasticutils.S.indexes

       .. automethod:: elasticutils.S.doctypes

       .. automethod:: elasticutils.S.explain

   **Methods to override if you need different behavior**

       .. automethod:: elasticutils.S.get_es

       .. automethod:: elasticutils.S.get_indexes

       .. automethod:: elasticutils.S.get_doctypes

       .. automethod:: elasticutils.S.to_python

   **Methods that force evaluation**

       .. automethod:: elasticutils.S.__iter__

       .. automethod:: elasticutils.S.__len__

       .. automethod:: elasticutils.S.all

       .. automethod:: elasticutils.S.count

       .. automethod:: elasticutils.S.execute

       .. automethod:: elasticutils.S.facet_counts


The F class
===========

.. autoclass:: elasticutils.F
   :members:


The Q class
===========

.. autoclass:: elasticutils.Q
   :members:


The SearchResults class
=======================

.. autoclass:: elasticutils.SearchResults
   :members:


The MappingType class
=====================

.. autoclass:: elasticutils.MappingType

   .. automethod:: elasticutils.MappingType.from_results

   .. automethod:: elasticutils.MappingType.get_object

   .. automethod:: elasticutils.MappingType.get_index

   .. automethod:: elasticutils.MappingType.get_mapping_type_name

   .. automethod:: elasticutils.MappingType.get_model


The Indexable class
===================

.. autoclass:: elasticutils.Indexable
   :members:


The DefaultMappingType class
============================

.. autoclass:: elasticutils.DefaultMappingType
   :members:


The MLT class
=============

.. autoclass:: elasticutils.MLT
   :members:

   .. automethod:: elasticutils.MLT.__init__

   .. automethod:: elasticutils.MLT.to_python


The ESTestCase class
====================

.. autoclass:: elasticutils.estestcase.ESTestCase
   :members:


Helper utilites
===============

.. autofunction:: elasticutils.utils.chunked

.. autofunction:: elasticutils.utils.format_explanation

.. autofunction:: elasticutils.utils.to_json
