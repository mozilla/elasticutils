from unittest import TestCase

from nose import SkipTest
import pyes

from elasticutils import get_es, S


class ElasticTestCase(TestCase):
    """Superclass for ElasticSearch-using test cases.

    :cvar index_name: string; name of the index to use
    :cvar skip_tests: bool; if ElasticSearch isn't available, then
        this is True and therefore tests should be skipped for this
        class

    For examples of usage, see the other ``test_*.py`` files.

    """
    index_name = 'elasticutilstest'
    mapping_type_name = 'elasticutilsmappingtype'

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
        if cls.skip_tests:
            return

        cls.cleanup_index()

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

    @classmethod
    def get_s(cls, mapping_type=None):
        if mapping_type is not None:
            s = S(mapping_type)
        else:
            s = S()
        return s.indexes(cls.index_name).doctypes(cls.mapping_type_name)

    @classmethod
    def create_index(cls):
        es = cls.get_es()
        try:
            es.delete_index_if_exists(cls.index_name)
        except pyes.exceptions.IndexMissingException:
            # pyes 0.15 throws an IndexMissingException despite the
            # fact that the method should allow for that.
            pass
        es.create_index(cls.index_name)

    @classmethod
    def index_data(cls, data, index=None, doctype=None, create_index=False):
        index = index or cls.index_name
        doctype = doctype or cls.mapping_type_name

        es = cls.get_es()

        if create_index:
            cls.create_index()

        for item in data:
            es.index(item, index, doctype, bulk=True, id=item['id'])

        es.flush_bulk(forced=True)
        cls.refresh()

    @classmethod
    def cleanup_index(cls):
        es = cls.get_es()
        es.delete_index_if_exists(cls.index_name)

    @classmethod
    def refresh(cls, timesleep=0):
        """Refresh index after indexing.

        This refreshes the index specified by `self.index_name`.

        :arg timesleep: int; number of seconds to sleep after telling
            ES to refresh

        """
        cls.get_es().refresh(cls.index_name, timesleep=timesleep)


def facet_counts_dict(qs, field):
    return dict((t['term'], t['count']) for t in qs.facet_counts()[field])
