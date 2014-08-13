from unittest import TestCase

from elasticsearch.helpers import bulk_index
try:
    from nose import SkipTest
except ImportError:
    try:
        from unittest.case import SkipTest
    except ImportError:
        class SkipTest(Exception):
            pass

from elasticutils import get_es, S


class ESTestCase(TestCase):
    """Superclass for Elasticsearch-using test cases.

    :property es_settings: settings to use to build a elasticsearch
        Elasticsearch object
    :property index_name: Name of the index to use for theses tests
    :property mapping_type_name: The mapping type name for the mapping
        you want created
    :property mapping: The mapping to use when creating the index
    :property data: Any documents to index during ``setup_class()``

    For examples of usage, see ``tests/test_*.py`` files.

    You probably want to subclass this and at least set relevant class
    properties. Then use that subclass as the superclass for your
    tests.

    """
    index_name = 'elasticutilstest'
    mapping_type_name = 'elasticutilsmappingtype'
    es_settings = {
        'urls': ['http://localhost:9200']
    }
    mapping = {}
    data = []

    @classmethod
    def setup_class(cls):
        """Sets up the index specified by ``cls.index_name``

        This will create the index named ``cls.index_name`` with the
        mapping specified in ``cls.mapping`` and indexes any data
        specified in ``cls.data``.

        If you need something different, then override this.

        """
        # Note: TestCase has no setup_class, so we don't call super()
        # here.
        cls.cleanup_index()
        cls.create_index(mappings=cls.mapping)
        if cls.data:
            cls.index_data(cls.data)
            cls.refresh()

    @classmethod
    def teardown_class(cls):
        """Removes the index specified by ``cls.index_name``

        This should clean up anything created in ``cls.setup_class()``
        and anything created by the tests.

        """
        cls.cleanup_index()

    def shortDescription(self):
        # Prevent the docstring being used as the test name because
        # that's irritating as all hell when trying to fix tests.
        pass

    @classmethod
    def get_es(cls):
        """Returns the Elasticsearch object specified by ``cls.es_settings``"""
        return get_es(**cls.es_settings)

    @classmethod
    def get_s(cls, mapping_type=None):
        """Returns an S for the settings on this class

        Uses ``cls.es_settings`` to configure the Elasticsearch
        object. Uses ``cls.index_name`` for the index and
        ``cls.mapping_type_name`` for the MappingType to search.

        :arg mapping_type: The MappingType class to use to create the S

        """
        if mapping_type is not None:
            s = S(mapping_type)
        else:
            s = S()
        return (s.es(**cls.es_settings)
                 .indexes(cls.index_name)
                 .doctypes(cls.mapping_type_name))

    @classmethod
    def create_index(cls, **kwargs):
        """Creates an index with specified settings

        Uses ``cls.index_name`` as the index to create.

        :arg kwargs: Any additional args to put in the body like
            "settings", "mappings", etc.

        """
        body = kwargs if kwargs else {}
        cls.get_es().indices.create(index=cls.index_name, body=body)

    @classmethod
    def index_data(cls, documents, id_field='id'):
        """Indexes specified data

        Uses ``cls.index_name`` as the index to index into.  Uses
        ``cls.mapping_type_name`` as the doctype to index these
        documents as.

        :arg documents: List of documents as Python dicts
        :arg id_field: The field of the document that represents the id

        """
        documents = (dict(d, _id=d[id_field]) for d in documents)
        bulk_index(cls.get_es(), documents, index=cls.index_name,
                   doc_type=cls.mapping_type_name)
        cls.refresh()

    @classmethod
    def cleanup_index(cls):
        """Cleans up the index

        This deletes the index named by ``cls.index_name``.

        """
        cls.get_es().indices.delete(index=cls.index_name, ignore=404)

    @classmethod
    def refresh(cls):
        """Refresh index after indexing

        This refreshes the index specified by ``cls.index_name``.

        """
        cls.get_es().indices.refresh(index=cls.index_name)
        cls.get_es().cluster.health(wait_for_status='yellow')
