import time
from distutils.version import LooseVersion
from functools import wraps
from unittest import TestCase

from nose import SkipTest
import elasticsearch

from elasticutils import get_es, S


class ESTestCase(TestCase):
    """Superclass for Elasticsearch-using test cases.

    :property index_name: name of the index to use
    :property mapping_type_name: the mapping type name
    :property es_settings: settings to use to build a elasticsearch
        Elasticsearch object.
    :property mapping: the mapping to use when creating an index
    :property data: any data to add to the index in setup_class
    :property skip_tests: if Elasticsearch isn't available, then this
        is True and therefore tests should be skipped for this class

    For examples of usage, see the other ``test_*.py`` files.

    """
    index_name = 'elasticutilstest'
    mapping_type_name = 'elasticutilsmappingtype'
    es_settings = {
        'urls': ['http://localhost:9200']
        }
    mapping = {}
    data = []
    skip_tests = False

    @classmethod
    def setup_class(cls):
        """Class setup for tests.

        Checks to see if ES is running and if not, sets ``skip_test``
        to True on the class.
        """
        # Note: TestCase has no setup_class
        try:
            get_es().cluster.health()
        except elasticsearch.TransportError:
            cls.skip_tests = True
            return

        if cls.data:
            cls.create_index(settings={'mappings': cls.mapping})
            cls.index_data(cls.data)
            cls.refresh()

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
        super(ESTestCase, self).setUp()

    @classmethod
    def get_es(cls):
        return get_es(**cls.es_settings)

    @classmethod
    def get_s(cls, mapping_type=None):
        if mapping_type is not None:
            s = S(mapping_type)
        else:
            s = S()
        return (s.es(**cls.es_settings)
                 .indexes(cls.index_name)
                 .doctypes(cls.mapping_type_name))

    @classmethod
    def create_index(cls, settings=None):
        es = cls.get_es()
        try:
            es.indices.delete(cls.index_name)
        except elasticsearch.NotFoundError:
            pass
        body = {}
        if settings:
            body['settings'] = settings
        es.indices.create(cls.index_name, body=body)

    @classmethod
    def index_data(cls, data, index=None, doctype=None):
        index = index or cls.index_name
        doctype = doctype or cls.mapping_type_name

        es = cls.get_es()

        # TODO: change this to a bulk index
        for item in data:
            es.index(index, doctype, item, id=item['id'])

        cls.refresh()

    @classmethod
    def cleanup_index(cls):
        es = cls.get_es()
        try:
            es.indices.delete(cls.index_name)
        except elasticsearch.NotFoundError:
            pass

    @classmethod
    def refresh(cls):
        """Refresh index after indexing.

        This refreshes the index specified by `self.index_name`.

        """
        cls.get_es().indices.refresh(cls.index_name)
        cls.get_es().cluster.health(wait_for_status='yellow')
    
    @classmethod
    def skip_unless_version(cls, min_version):
        """Checks that the available elasticsearch server is at least the `min_version` supplied.

        : arg min_version: tuple of version numbers that represent the minimum version required.

        """
        es = cls.get_es()
        info = es.info()
        number_string = info['version']['number']
        number = tuple([int(x) for x in number_string.split('.')])
        if number < min_version:
            raise SkipTest("Test requires minimum version of {}".format(min_version))


def facet_counts_dict(qs, field):
    return dict((t['term'], t['count']) for t in qs.facet_counts()[field])


def require_version(minimum_version):
    """Skip the test if the Elasticsearch version is less than specified.

    :arg minimum_version: string; the minimum Elasticsearch version required

    """

    def decorated(test):
        """Decorator to only run the test if ES version is greater or
        equal than specified.

        """

        @wraps(test)
        def test_with_version(self):
            "Only run the test if ES version is not less than specified."
            actual_version = self.get_es().info()['version']['number']

            if LooseVersion(actual_version) >= LooseVersion(minimum_version):
                test(self)
            else:
                raise SkipTest

        return test_with_version

    return decorated
