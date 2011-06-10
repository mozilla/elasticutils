"""
With `test_utils` you can use this testcase.
"""
from django.conf import settings

import test_utils
from elasticutils import get_es


class ESTestCase(test_utils.TestCase):
    """
    ESTestCase turns ElasticSearch on, shuts it down at the end of the tests.
    """
    @classmethod
    def setup_class(cls):
        if not hasattr(settings, 'ES_HOSTS'):
            raise SkipTest
        cls.old_ES_DISABLED = settings.ES_DISABLED
        settings.__dict__['ES_DISABLED'] = False

        cls.es = get_es()
        cls.es.delete_index_if_exists(settings.ES_INDEX)

    def tearDown(self):
        self.es.delete_index_if_exists(settings.ES_INDEX)

    @classmethod
    def teardown_class(cls):
        settings.__dict__['ES_DISABLED'] = cls.old_ES_DISABLED
