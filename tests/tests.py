"""
Run me using nose!

Also run elastic search on the default ports locally.
"""
from unittest import TestCase

from elasticutils import F, S, get_es
from nose.tools import eq_


class QueryTest(TestCase):

    @classmethod
    def setup_class(cls):
        es = get_es()
        data1 = dict(id=1, foo='bar', tag='awesome', width='2')
        data2 = dict(id=2, foo='barf', tag='boring', width='7')
        data3 = dict(id=3, foo='car', tag='awesome', width='5')
        data4 = dict(id=4, foo='duck', tag='boat', width='11')
        data5 = dict(id=5, foo='train car', tag='awesome', width='7')

        for data in (data1, data2, data3, data4, data5):
            es.index(data, 'test', 'boondongles', bulk=True)
        es.refresh()

    def test_q(self):
        eq_(len(S('bar', type='boondongles')), 1)
        eq_(len(S('car', type='boondongles')), 2)

    def test_q_all(self):
        eq_(len(S()), 5)

    def test_filter(self):
        eq_(len(S(tag='awesome')), 3)

    def test_filter_and(self):
        eq_(len(S(tag='awesome', foo='bar')), 1)

    def test_filter_or(self):
        eq_(len(S().filter(F(tag='awesome') | F(tag='boat'))), 4)

    def test_filter_or_3(self):
        eq_(len(S().filter(F(tag='awesome') | F(tag='boat') |
                           F(tag='boring'))), 5)
        eq_(len(S().filter(F(foo='bar') |
                           (F(tag='boat') | F(tag='boring')))), 3)

    def test_filter_complicated(self):
        eq_(len(S().filter(F(tag='awesome', foo='bar') | F(tag='boring'))), 2)

    def test_facet(self):
        eq_(S().facet('tag').get_facet('tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_custom_score(self):
        """
        This query selects all the boondongles with the tag 'awesome' and then
        applies the custom score script to rank them based on their 'width'
        parameter. Since the tag being queried for matches exactly, each starts
        with a score of 1.0. The script then multiplies that by the width to
        get their final scores; hence, the calculated scores will be equal to
        the width. The results are ordered by highest score first, so we can
        expect them to be id 5 with a score of 7.0, then id 3 with a score of
        5.0, then id 1 with a score of 2.0.
        """
        res = S(tag='awesome')
        res = res.score(script='_score * doc["width"].value').get_results()
        eq_([d['_source']['id'] for d in res], [5, 3, 1])

    @classmethod
    def teardown_class(cls):
        es = get_es()
        es.delete_index('test')
