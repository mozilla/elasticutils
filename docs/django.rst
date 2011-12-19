========================
Django Model Integration
========================

Django Models and ElasticSearch indices make a natural fit.
It would be terribly useful if a Django Model knew how to add and remove itself
from ElasticSearch.
This is where the :class:`elasticutils.models.SearchMixin` comes in.

.. autoclass:: elasticutils.models.SearchMixin
   :members:

