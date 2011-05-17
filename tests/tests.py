"""
Run me using nose!

Also run elastic search on the default ports locally.
"""
from unittest import TestCase

from elasticutils import Q, get_es
from nose.tools import eq_


class QueryTest(TestCase):

    @classmethod
    def setup_class(cls):
        es = get_es()
        data1 = dict(id=1, foo='bar', tag='awesome')
        data2 = dict(id=2, foo='barf', tag='boring')
        data3 = dict(id=3, foo='car', tag='awesome')
        data4 = dict(id=4, foo='duck', tag='boat')
        data5 = dict(id=5, foo='train car', tag='awesome')

        for data in (data1, data2, data3, data4, data5):
            es.index(data, 'test', 'boondongles', bulk=True)
        es.refresh()

    def test_q(self):
        eq_(len(Q('bar', type='boondongles')), 1)
        eq_(len(Q('car', type='boondongles')), 2)

    def test_q_all(self):
        eq_(len(Q()), 5)

    def test_filter(self):
        eq_(len(Q(tag='awesome')), 3)

    def test_facet(self):
        eq_(Q().facet('tag').get_facet('tag'),
            dict(awesome=3, boring=1, boat=1))

    @classmethod
    def teardown_class(cls):
        es = get_es()
        es.delete_index('test')
