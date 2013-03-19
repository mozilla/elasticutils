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
    return [(k, v + '_eutest') for k, v in indexes.items()]


class ElasticSearchTestCase(TestCase):
    """Test case scaffolding for ElasticUtils-using tests.

    If ``ES_URLS`` is empty or missing or you can't connect to
    ElasticSearch specified in ``ES_URLS``, then this will skip each
    individual test. This works with py.test, nose, and unittest in
    Python 2.7. If you don't have one of those, then this will print
    to stdout and just skip the test silently.

    """
    _skip_tests = False

    @classmethod
    def setUpClass(cls):
        super(ElasticSearchTestCase, cls).setUpClass()
        if not getattr(settings, 'ES_URLS', None):
            cls._skip_tests = True
            return

        try:
            get_es().health()
        except (Timeout, ConnectionError):
            cls._skip_tests = True
            return

        # Save settings and override them
        cls._old_es_disabled = settings.ES_DISABLED
        settings.ES_DISABLED = False

        cls._old_es_indexes = settings.ES_INDEXES
        settings.ES_INDEXES = testify(settings.ES_INDEXES)

        cls.es = get_es()
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index(index)
            except ElasticHttpNotFoundError:
                pass

    def setUp(self):
        if self._skip_tests:
            return skip_this_test()
        super(ElasticSearchTestCase, self).setUp()

    @classmethod
    def tearDownClass(cls):
        if not cls._skip_test:
            for index in settings.ES_INDEXES.values():
                try:
                    cls.es.delete_index(index)
                except ElasticHttpNotFoundError:
                    pass

        # Restor settings
        settings.ES_DISABLED = cls._old_es_disabled
        settings.ES_INDEXES = cls._old_es_indexes

        super(ElasticSearchTestCase, cls).tearDownClass()
