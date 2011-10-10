"""
Run me using nose!

Also run elastic search on the default ports locally.
"""
from unittest import TestCase

from elasticutils import F, S, get_es
from nose.tools import eq_


class Meta(object):
    def __init__(self, db_table):
        self.db_table = db_table


class Manager(object):
    def filter(self, id__in=None):
        return [m for m in model_cache if m.id in id__in]

model_cache = []


class FakeModel(object):
    _meta = Meta('fake')
    objects = Manager()

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])
        model_cache.append(self)


class QueryTest(TestCase):

    @classmethod
    def setup_class(cls):
        es = get_es()
        es.delete_index_if_exists('test')
        data1 = FakeModel(id=1, foo='bar', tag='awesome', width='2')
        data2 = FakeModel(id=2, foo='barf', tag='boring', width='7')
        data3 = FakeModel(id=3, foo='car', tag='awesome', width='5')
        data4 = FakeModel(id=4, foo='duck', tag='boat', width='11')
        data5 = FakeModel(id=5, foo='train car', tag='awesome', width='7')

        for data in (data1, data2, data3, data4, data5):
            es.index(data.__dict__, 'test', FakeModel._meta.db_table,
                    bulk=True, id=data.id)
        es.refresh()

    def test_q(self):
        eq_(len(S(FakeModel).query(foo='bar')), 1)
        eq_(len(S(FakeModel).query(foo='car')), 2)

    def test_q_all(self):
        eq_(len(S(FakeModel)), 5)

    def test_filter(self):
        eq_(len(S(FakeModel).filter(tag='awesome')), 3)
        eq_(len(S(FakeModel).filter(F(tag='awesome'))), 3)

    def test_filter_and(self):
        eq_(len(S(FakeModel).filter(tag='awesome', foo='bar')), 1)
        eq_(len(S(FakeModel).filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(S(FakeModel).filter(F(tag='awesome') & F(foo='bar'))), 1)

    def test_filter_or(self):
        eq_(len(S(FakeModel).filter(F(tag='awesome') | F(tag='boat'))), 4)

    def test_filter_or_3(self):
        eq_(len(S(FakeModel).filter(F(tag='awesome') | F(tag='boat') |
                                    F(tag='boring'))), 5)
        eq_(len(S(FakeModel).filter(or_={'foo': 'bar', 'or_': {'tag': 'boat',
                                    'width': '5'}})), 3)

    def test_filter_complicated(self):
        eq_(len(S(FakeModel).filter(F(tag='awesome', foo='bar') |
            F(tag='boring'))), 2)

    def test_filter_not(self):
        eq_(len(S(FakeModel).filter(~F(tag='awesome'))), 2)
        eq_(len(S(FakeModel).filter(~(F(tag='boring') | F(tag='boat')))), 3)
        eq_(len(S(FakeModel).filter(~F(tag='boat')).filter(~F(foo='bar'))), 3)
        eq_(len(S(FakeModel).filter(~F(tag='boat', foo='barf'))), 5)

    def test_facet(self):
        qs = S(FakeModel).facet(tags={'terms': {'field': 'tag'}})
        tag_counts = dict((t['term'], t['count']) for t in qs.facets['tags'])

        eq_(tag_counts, dict(awesome=3, boring=1, boat=1))

    def test_order_by(self):
        res = S(FakeModel).filter(tag='awesome').order_by('-width')
        eq_([d.id for d in res], [5, 3, 1])

    def test_repr(self):
        res = S(FakeModel)[:2]
        list_ = list(res)

        eq_(repr(list_), repr(res))

    @classmethod
    def teardown_class(cls):
        es = get_es()
        es.delete_index('test')
