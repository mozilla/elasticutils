"""
With `test_utils` you can use this testcase.
"""
from django.test import TestCase

from django.conf import settings
from elasticsearch.exceptions import ConnectionError, NotFoundError
from elasticsearch.helpers import bulk_index

# Try really really hard to find a valid skip thing.
try:
    from nose import SkipTest
    def skip_this_test():
        raise SkipTest
except ImportError:
    try:
        import pytest
        def skip_this_test():
            pytest.skip('skipping: es not set up')
    except ImportError:
        try:
            from unittest import skip
            def skip_this_test():
                skip('skipping: es not set up')
        except ImportError:
            def skip_this_test():
                print 'SKIPPING: es not set up'
                return


from elasticutils import get_es


def testify(indexes):
    """Returns indexes with '_eutest' suffix.
    
    :arg indexes: dict of mapping type name -> index name(s)
    
    :returns: dict with ``_eutest`` appended to all index names
    
    """
    ret = {}
    for k, v in indexes.items():
        if isinstance(v, basestring):
            ret[k] = v + '_eutest'
        elif isinstance(v, (list, tuple)):
            ret[k] = [v_item + '_eutest' for v_item in v]
    return ret


class ESTestCase(TestCase):
    """Test case scaffolding for ElasticUtils-using tests.

    If ``ES_URLS`` is empty or missing or you can't connect to
    Elasticsearch specified in ``ES_URLS``, then this will skip each
    individual test. This works with py.test, nose, and unittest in
    Python 2.7. If you don't have one of those, then this will print
    to stdout and just skip the test silently.

    """
    skip_tests = False

    @classmethod
    def setUpClass(cls):
        """Sets up the environment for ES tests

        * pings the ES server---if this fails, it marks all the tests
          for skipping
        * fixes settings
        * deletes the test index if there is one

        """
        super(ESTestCase, cls).setUpClass()
        if not getattr(settings, 'ES_URLS', None):
            cls.skip_tests = True
            return

        try:
            cls.get_es().cluster.health()
        except ConnectionError:
            cls.skip_tests = True
            return

        # Save settings and override them
        cls._old_es_disabled = settings.ES_DISABLED
        settings.ES_DISABLED = False

        cls._old_es_indexes = settings.ES_INDEXES
        settings.ES_INDEXES = testify(settings.ES_INDEXES)

        # This is here in case the previous test run failed and didn't
        # clean up after itself.
        for index in settings.ES_INDEXES.values():
            cls.get_es().indices.delete(index=index, ignore=404)

    def setUp(self):
        """Skips the test if this class is skipping tests."""
        if self.skip_tests:
            return skip_this_test()
        super(ESTestCase, self).setUp()

    @classmethod
    def tearDownClass(cls):
        """Tears down environment

        * unfixes settings
        * deletes the test index

        """
        if not cls.skip_tests:
            # If we didn't skip these tests, we need to do some
            # cleanup.
            for index in settings.ES_INDEXES.values():
                cls.cleanup_index(index)

            # Restore settings
            settings.ES_DISABLED = cls._old_es_disabled
            settings.ES_INDEXES = cls._old_es_indexes

        super(ESTestCase, cls).tearDownClass()

    @classmethod
    def get_es(cls):
        """Returns an ES

        Override this if you need different settings for your
        ES.

        """
        return get_es()

    @classmethod
    def create_index(cls, index, settings=None):
        """Creates index with given settings

        :arg index: the name of the index to create
        :arg settings: dict of settings to set in `create_index` call

        """
        settings = settings or {}

        cls.get_es().indices.create(index=index, **settings)

    @classmethod
    def index_data(cls, documents, index, doctype, id_field='id'):
        """Bulk indexes given data.

        This does a refresh after the data is indexed.

        :arg documents: list of python dicts each a document to index
        :arg index: name of the index
        :arg doctype: mapping type name
        :arg id_field: the field the document id is stored in in the
            document

        """
        documents = (dict(d, _id=d[id_field]) for d in documents)
        bulk_index(cls.get_es(), documents, index=index, doc_type=doctype)
        cls.refresh(index)

    @classmethod
    def cleanup_index(cls, index):
        cls.get_es().indices.delete(index=index, ignore=404)

    @classmethod
    def refresh(cls, index):
        """Refresh index after indexing.

        :arg index: the name of the index to refresh. use ``_all``
            to refresh all of them

        """
        cls.get_es().indices.refresh(index=index)
        cls.get_es().cluster.health(wait_for_status='yellow')
