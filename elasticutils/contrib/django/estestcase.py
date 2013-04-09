"""
With `test_utils` you can use this testcase.
"""
from unittest import TestCase

from django.conf import settings
from pyelasticsearch.exceptions import (
    Timeout, ConnectionError, ElasticHttpNotFoundError)

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
    
    :arg indexes: dict of mapping type name -> index name
    
    :returns: dict with ``_eutest`` appended to all index names
    
    """
    return dict([(k, v + '_eutest') for k, v in indexes.items()])


class ElasticSearchTestCase(TestCase):
    """Test case scaffolding for ElasticUtils-using tests.

    If ``ES_URLS`` is empty or missing or you can't connect to
    ElasticSearch specified in ``ES_URLS``, then this will skip each
    individual test. This works with py.test, nose, and unittest in
    Python 2.7. If you don't have one of those, then this will print
    to stdout and just skip the test silently.

    """
    skip_tests = False

    @classmethod
    def setUpClass(cls):
        super(ElasticSearchTestCase, cls).setUpClass()
        if not getattr(settings, 'ES_URLS', None):
            cls.skip_tests = True
            return

        try:
            get_es().health()
        except (Timeout, ConnectionError):
            cls.skip_tests = True
            return

        # Save settings and override them
        cls._old_es_disabled = settings.ES_DISABLED
        settings.ES_DISABLED = False

        cls._old_es_indexes = settings.ES_INDEXES
        settings.ES_INDEXES = testify(settings.ES_INDEXES)

    def setUp(self):
        if self.skip_tests:
            return skip_this_test()
        super(ElasticSearchTestCase, self).setUp()

    @classmethod
    def tearDownClass(cls):
        if not cls.skip_tests:
            for index in settings.ES_INDEXES.values():
                try:
                    cls.es.delete_index(index)
                except ElasticHttpNotFoundError:
                    pass

        # Restor settings
        settings.ES_DISABLED = cls._old_es_disabled
        settings.ES_INDEXES = cls._old_es_indexes

        super(ElasticSearchTestCase, cls).tearDownClass()

    @classmethod
    def create_index(cls):
        cls.cleanup_index()

        for index in settings.ES_INDEXES.values():
            try:
                cls.es.create_index(cls.index_name)
            except ElasticHttpNotFoundError:
                pass

    @classmethod
    def index_data(cls, data, index=None, doctype=None):
        index = index or cls.index_name
        doctype = doctype or cls.mapping_type_name

        # TODO: change this to a bulk index
        for item in data:
            cls.es.index(index, doctype, item, id=item['id'])

        cls.refresh()

    @classmethod
    def cleanup_index(cls):
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index(index)
            except ElasticHttpNotFoundError:
                pass

    @classmethod
    def refresh(cls):
        """Refresh index after indexing.

        This refreshes the index specified by `self.index_name`.

        """
        cls.es.refresh(cls.index_name)
        cls.es.health(wait_for_status='yellow')
