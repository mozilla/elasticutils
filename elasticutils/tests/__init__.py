from unittest import TestCase

from nose import SkipTest
import pyes

from elasticutils import get_es


model_cache = []

def reset_model_cache():
    del model_cache[0:]

class Meta(object):
    def __init__(self, db_table):
        self.db_table = db_table


class Manager(object):
    def filter(self, id__in=None):
        return [m for m in model_cache if m.id in id__in]


class FakeModel(object):
    _meta = Meta('fake')
    objects = Manager()

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])
        model_cache.append(self)


class ElasticTestCase(TestCase):
    """Superclass for ElasticSearch-using test cases.

    :cvar index_name: string; name of the index to use
    :cvar skip_tests: bool; if ElasticSearch isn't available, then
        this is True and therefore tests should be skipped for this
        class

    For examples of usage, see the other ``test_*.py`` files.

    """
    index_name = 'elasticutilstest'
    skip_tests = False

    @classmethod
    def setup_class(cls):
        """Class setup for tests.

        Checks to see if ES is running and if not, sets ``skip_test``
        to True on the class.
        """
        # Note: TestCase has no setup_class
        try:
            get_es().collect_info()
        except pyes.urllib3.MaxRetryError:
            cls.skip_tests = True

    @classmethod
    def teardown_class(cls):
        """Class tear down for tests."""
        reset_model_cache()

    def setUp(self):
        """Set up a single test.

        :raises SkipTest: if ``skip_tests`` is True for this
            class/instance
        """
        if self.skip_tests:
            raise SkipTest

        super(ElasticTestCase, self).setUp()

    @classmethod
    def get_es(cls):
        return get_es(default_indexes=[cls.index_name])

    def refresh(self, timesleep=0):
        """Refresh index after indexing.

        This refreshes the index specified by `self.index_name`.

        :arg timesleep: int; number of seconds to sleep after telling
            ES to refresh

        """
        get_es().refresh(self.index_name, timesleep=timesleep)


def facet_counts_dict(qs, field):
    return dict((t['term'], t['count']) for t in qs.facet_counts()[field])
