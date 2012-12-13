"""
With `test_utils` you can use this testcase.
"""
from django.conf import settings

import test_utils
import pyelasticsearch
from elasticutils import get_es
from nose import SkipTest


class ElasticSearchTestCase(test_utils.TestCase):
    """
    ElasticSearchTestCase turns ElasticSearch on, shuts it down at the
    end of the tests.
    """
    @classmethod
    def setUpClass(cls):
        super(ElasticSearchTestCase, cls).setUpClass()
        if not (hasattr(settings, 'ES_URLS') and settings.ES_URLS):
            raise SkipTest
        cls.old_ES_DISABLED = settings.ES_DISABLED
        settings.__dict__['ES_DISABLED'] = False

        cls.es = get_es()
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index(index)
            except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
                pass

    @classmethod
    def tearDownClass(cls):
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index(index)
            except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
                pass
        settings.__dict__['ES_DISABLED'] = cls.old_ES_DISABLED
        super(ElasticSearchTestCase, cls).tearDownClass()
