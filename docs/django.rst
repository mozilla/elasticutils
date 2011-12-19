========================
Django Model Integration
========================

Django Models and ElasticSearch indices make a natural fit.
It would be terribly useful if a Django Model knew how to add and remove itself
from ElasticSearch.
This is where the :class:`elasticutils.models.SearchMixin` comes in.

You can then utilize things such as :func:`~elasticutils.tasks.index_objects` to
automatically index all new items.

.. autoclass:: elasticutils.models.SearchMixin
   :members:

.. automodule:: elasticutils.tasks

   .. autofunction:: index_objects(model, ids=[...])

.. automodule:: elasticutils.cron

   .. autofunction:: reindex_objects(model, chunk_size[=150])
