from functools import wraps
from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_
import pyes.exceptions

from elasticutils.tests import ElasticTestCase, facet_counts_dict


# TODO: To run this file or import it requires Django be installed.
# If Django isn't installed, we want to skip each test individually.
# However, those requirements create a lot of tangled stuff in here.
# It'd be nice if we could do this in a less tangled way and also skip
# the tests individually (so it's easy to see which tests got skipped
# and why) if Django isn't installed.


SKIP_TESTS = False


try:
    from django.conf import settings

    from elasticutils.contrib.django import (
        S, F, get_es, InvalidFieldActionError)
    from elasticutils.tests.django_utils import (
        FakeDjangoMappingType, FakeModel)
except ImportError:
    SKIP_TESTS = True


def requires_django(fun):
    @wraps(fun)
    def _requires_django(*args, **kwargs):
        if SKIP_TESTS:
            raise SkipTest
        return fun(*args, **kwargs)
    return _requires_django


class TestS(TestCase):
    @requires_django
    def test_require_mapping_type(self):
        """The Django S requires a mapping type."""
        self.assertRaises(TypeError, S)

    @requires_django
    def test_get_indexes(self):
        """Test get_indexes always returns a list of strings."""

        # Pulls it from ES_INDEXES (list of strings).
        s = S(FakeDjangoMappingType)
        eq_(s.get_indexes(), ['elasticutilstest'])

        # Pulls it from ES_INDEXES (string).
        old_indexes = settings.ES_INDEXES
        try:
            settings.ES_INDEXES = {'default': 'elasticutilstest'}

            s = S(FakeDjangoMappingType)
            eq_(s.get_indexes(), ['elasticutilstest'])
        finally:
            settings.ES_INDEXES = old_indexes

        # Pulls from indexes.
        s = S(FakeDjangoMappingType).indexes('footest')
        eq_(s.get_indexes(), ['footest'])

        s = S(FakeDjangoMappingType).indexes('footest', 'footest2')
        eq_(s.get_indexes(), ['footest', 'footest2'])

        s = S(FakeDjangoMappingType).indexes('footest').indexes('footest2')
        eq_(s.get_indexes(), ['footest2'])

    @requires_django
    def test_get_doctypes(self):
        """Test get_doctypes always returns a list of strings."""
        # Pulls from ._meta.db_table.
        s = S(FakeDjangoMappingType)
        eq_(s.get_doctypes(), ['fake'])

        # Pulls from doctypes.
        s = S(FakeDjangoMappingType).doctypes('footype')
        eq_(s.get_doctypes(), ['footype'])

        s = S(FakeDjangoMappingType).doctypes('footype', 'footype2')
        eq_(s.get_doctypes(), ['footype', 'footype2'])

        s = S(FakeDjangoMappingType).doctypes('footype').doctypes('footype2')
        eq_(s.get_doctypes(), ['footype2'])


class ESTest(TestCase):
    @requires_django
    def test_get_es_defaults(self):
        """Test that the ES has the correct defaults."""
        es = get_es()
        eq_(es.timeout, settings.ES_TIMEOUT)
        # dump_curl defaults to False, but if dump_curl is Falsey,
        # then pyes.es.ES sets its dump_curl attribute to None.
        eq_(es.dump_curl, None)
        eq_(es.default_indexes, [settings.ES_INDEXES['default']])

    @requires_django
    def test_get_es_overriding_defaults(self):
        """Test that overriding defaults works."""
        class Dumper(object):
            def write(self, val):
                print val

        d = Dumper()

        es = get_es(timeout=20,
                    dump_curl=d,
                    default_indexes=['joe'])

        eq_(es.timeout, 20)
        eq_(es.dump_curl, d)
        eq_(es.default_indexes, ['joe'])


class QueryTest(ElasticTestCase):
    @classmethod
    def setup_class(cls):
        super(QueryTest, cls).setup_class()
        if cls.skip_tests or SKIP_TESTS:
            return

        cls.create_index()

        data = [
            {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
            {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
            {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
            {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
            {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
            ]
        cls.index_data(data,
                       index=FakeDjangoMappingType.get_index(),
                       doctype=FakeDjangoMappingType.get_mapping_type_name())

        # Generate all the FakeModels in our "database"
        for args in data:
            FakeModel(**args)

        cls.refresh()

    @requires_django
    def test_q(self):
        eq_(len(S(FakeDjangoMappingType).query(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).query(foo='car')), 2)

    @requires_django
    def test_q_all(self):
        eq_(len(S(FakeDjangoMappingType)), 5)

    @requires_django
    def test_filter_empty_f(self):
        eq_(len(S(FakeDjangoMappingType).filter(F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() | F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F())), 5)

    @requires_django
    def test_filter(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome')), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome'))), 3)

    @requires_django
    def test_filter_and(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome', foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') & F(foo='bar'))), 1)

    @requires_django
    def test_filter_or(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat'))), 4)

    @requires_django
    def test_filter_or_3(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat') |
                                     F(tag='boring'))), 5)
        eq_(len(S(FakeDjangoMappingType).filter(or_={'foo': 'bar',
                                          'or_': {'tag': 'boat',
                                                  'width': '5'}
                                          })), 3)

    @requires_django
    def test_filter_complicated(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    @requires_django
    def test_filter_not(self):
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='awesome'))), 2)
        eq_(len(S(FakeDjangoMappingType).filter(~(F(tag='boring') | F(tag='boat')))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat')).filter(~F(foo='bar'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat', foo='barf'))), 5)

    @requires_django
    def test_filter_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(S(FakeDjangoMappingType).filter(F(tag__faux='awesome')))

    @requires_django
    def test_facet(self):
        qs = S(FakeDjangoMappingType).facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_filtered_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    @requires_django
    def test_global_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_facet_raw(self):
        qs = S(FakeDjangoMappingType).facet_raw(tags={'terms': {'field': 'tag'}})
        eq_(facet_counts_dict(qs, 'tags'),
            dict(awesome=3, boring=1, boat=1))

        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet_raw(tags={'terms': {'field': 'tag'}}))
        eq_(facet_counts_dict(qs, 'tags'),
            {'awesome': 2})

    @requires_django
    def test_facet_raw_overrides_facet(self):
        """facet_raw overrides facet with the same facet name."""
        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_order_by(self):
        res = S(FakeDjangoMappingType).filter(tag='awesome').order_by('-width')
        eq_([d.id for d in res], [5, 3, 1])

    @requires_django
    def test_repr(self):
        res = S(FakeDjangoMappingType)[:2]
        list_ = list(res)

        eq_(repr(list_), repr(res))
