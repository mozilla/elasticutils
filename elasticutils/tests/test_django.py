from functools import wraps
from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_
import pyes.exceptions

from elasticutils.tests import FakeModel, ElasticTestCase, facet_counts_dict


# TODO: To run this file or import it requires Django be installed.
# If Django isn't installed, we want to skip each test individually.
# However, those requirements create a lot of tangled stuff in here.
# It'd be nice if we could do this in a less tangled way and also skip
# the tests individually (so it's easy to see which tests got skipped
# and why) if Django isn't installed.


def requires_django(fun):
    @wraps(fun)
    def _requires_django(*args, **kwargs):
        try:
            import django
        except ImportError:
            raise SkipTest
        return fun(*args, **kwargs)
    return _requires_django


class STest(TestCase):
    @requires_django
    def test_require_type_(self):
        """The Django S requires a type_."""
        from elasticutils.contrib.django import S
        with self.assertRaises(TypeError):
            S()


class ESTest(TestCase):
    @requires_django
    def test_get_es_defaults(self):
        """Test that the ES has the correct defaults."""
        from django.conf import settings
        from elasticutils.contrib.django import get_es

        es = get_es()
        eq_(es.timeout, settings.ES_TIMEOUT)
        # dump_curl defaults to False, but if dump_curl is Falsey,
        # then pyes.es.ES sets its dump_curl attribute to None.
        eq_(es.dump_curl, None)
        eq_(es.default_indexes, [settings.ES_INDEXES['default']])

    @requires_django
    def test_get_es_overriding_defaults(self):
        """Test that overriding defaults works."""
        from elasticutils.contrib.django import get_es

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
        if cls.skip_tests:
            return

        try:
            import django
        except ImportError:
            cls.skip_tests = True
            return

        from elasticutils.contrib.django import get_es

        es = get_es()
        try:
            es.delete_index_if_exists(cls.index_name)
        except pyes.exceptions.IndexMissingException:
            # TODO: No clue why this is throwing an IndexMissingException
            # because I thought the whole point of delete_index_if_exists
            # is that it _didn't_ throw an exception if the index was
            # missing.
            pass
        data1 = FakeModel(id=1, foo='bar', tag='awesome', width='2')
        data2 = FakeModel(id=2, foo='barf', tag='boring', width='7')
        data3 = FakeModel(id=3, foo='car', tag='awesome', width='5')
        data4 = FakeModel(id=4, foo='duck', tag='boat', width='11')
        data5 = FakeModel(id=5, foo='train car', tag='awesome', width='7')

        for data in (data1, data2, data3, data4, data5):
            es.index(data.__dict__, cls.index_name, FakeModel._meta.db_table,
                    bulk=True, id=data.id)
        es.refresh()

    @classmethod
    def teardown_class(cls):
        super(QueryTest, cls).teardown_class()
        if cls.skip_tests:
            return

        from elasticutils.contrib.django import get_es

        es = get_es()
        es.delete_index(cls.index_name)

    @requires_django
    def test_q(self):
        from elasticutils.contrib.django import S

        eq_(len(S(FakeModel).query(foo='bar')), 1)
        eq_(len(S(FakeModel).query(foo='car')), 2)

    @requires_django
    def test_q_all(self):
        from elasticutils.contrib.django import S

        eq_(len(S(FakeModel)), 5)

    @requires_django
    def test_filter_empty_f(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeModel).filter(F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeModel).filter(F() | F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeModel).filter(F() & F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeModel).filter(F())), 5)

    @requires_django
    def test_filter(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(tag='awesome')), 3)
        eq_(len(S(FakeModel).filter(F(tag='awesome'))), 3)

    @requires_django
    def test_filter_and(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(tag='awesome', foo='bar')), 1)
        eq_(len(S(FakeModel).filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(S(FakeModel).filter(F(tag='awesome') & F(foo='bar'))), 1)

    @requires_django
    def test_filter_or(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(F(tag='awesome') | F(tag='boat'))), 4)

    @requires_django
    def test_filter_or_3(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(F(tag='awesome') | F(tag='boat') |
                                     F(tag='boring'))), 5)
        eq_(len(S(FakeModel).filter(or_={'foo': 'bar',
                                          'or_': {'tag': 'boat',
                                                  'width': '5'}
                                          })), 3)

    @requires_django
    def test_filter_complicated(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    @requires_django
    def test_filter_not(self):
        from elasticutils.contrib.django import S, F

        eq_(len(S(FakeModel).filter(~F(tag='awesome'))), 2)
        eq_(len(S(FakeModel).filter(~(F(tag='boring') | F(tag='boat')))), 3)
        eq_(len(S(FakeModel).filter(~F(tag='boat')).filter(~F(foo='bar'))), 3)
        eq_(len(S(FakeModel).filter(~F(tag='boat', foo='barf'))), 5)

    @requires_django
    def test_filter_bad_field_action(self):
        from elasticutils.contrib.django import S, F, InvalidFieldActionError

        with self.assertRaises(InvalidFieldActionError):
            len(S(FakeModel).filter(F(tag__faux='awesome')))

    @requires_django
    def test_facet(self):
        from elasticutils.contrib.django import S

        qs = S(FakeModel).facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_filtered_facet(self):
        from elasticutils.contrib.django import S

        qs = S(FakeModel).query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    @requires_django
    def test_global_facet(self):
        from elasticutils.contrib.django import S

        qs = S(FakeModel).query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_facet_raw(self):
        from elasticutils.contrib.django import S

        qs = S(FakeModel).facet_raw(tags={'terms': {'field': 'tag'}})
        eq_(facet_counts_dict(qs, 'tags'),
            dict(awesome=3, boring=1, boat=1))

        qs = (S(FakeModel)
              .query(foo='car')
              .facet_raw(tags={'terms': {'field': 'tag'}}))
        eq_(facet_counts_dict(qs, 'tags'),
            {'awesome': 2})

    @requires_django
    def test_facet_raw_overrides_facet(self):
        """facet_raw overrides facet with the same facet name."""
        from elasticutils.contrib.django import S

        qs = (S(FakeModel)
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @requires_django
    def test_order_by(self):
        from elasticutils.contrib.django import S

        res = S(FakeModel).filter(tag='awesome').order_by('-width')
        eq_([d.id for d in res], [5, 3, 1])

    @requires_django
    def test_repr(self):
        from elasticutils.contrib.django import S

        res = S(FakeModel)[:2]
        list_ = list(res)

        eq_(repr(list_), repr(res))
