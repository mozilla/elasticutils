"""
With `test_utils` you can use this testcase.
"""
from django.conf import settings

import test_utils
import pyes.exceptions
from elasticutils import get_es
from nose import SkipTest


class ESTestCase(test_utils.TestCase):
    """
    ESTestCase turns ElasticSearch on, shuts it down at the end of the tests.
    """
    @classmethod
    def setUpClass(cls):
        super(ESTestCase, cls).setUpClass()
        if not (hasattr(settings, 'ES_HOSTS') and settings.ES_HOSTS):
            raise SkipTest
        cls.old_ES_DISABLED = settings.ES_DISABLED
        settings.__dict__['ES_DISABLED'] = False

        cls.es = get_es()
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index_if_exists(index)
            except pyes.exceptions.IndexMissingException:
                pass

    @classmethod
    def tearDownClass(cls):
        for index in settings.ES_INDEXES.values():
            try:
                cls.es.delete_index_if_exists(index)
            except pyes.exceptions.IndexMissingException:
                pass
        settings.__dict__['ES_DISABLED'] = cls.old_ES_DISABLED
        super(ESTestCase, cls).tearDownClass()
