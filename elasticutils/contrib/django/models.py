from django.conf import settings

from pyes import djangoutils

import elasticutils


class SearchMixin(object):
    """This mixin correlates a Django model to an ElasticSearch index."""

    @classmethod
    def _get_index(cls):
        indexes = settings.ES_INDEXES
        return indexes.get(cls._meta.db_table) or indexes['default']

    @classmethod
    def index(cls, document, id=None, bulk=False, force_insert=False):
        """Associates a document with a correlated id in ES.

        Wrapper around pyes.ES.index.

        Example::

            MyModel.index(instance.fields, id=instance.id)
        """
        elasticutils.get_es().index(
            document, index=cls._get_index(), doc_type=cls._meta.db_table,
            id=id, bulk=bulk, force_insert=force_insert)

    @classmethod
    def unindex(cls, id):
        """Removes a particular item from the search index."""
        elasticutils.get_es().delete(cls._get_index(), cls._meta.db_table, id)

    def fields(self):
        """Returns a serialization of a Model instance.

        This can be used for indexing data.

        .. warning::
            It is recommended that you override this method and selectively
            serialize fields.
        """
        return djangoutils.get_values(self)
