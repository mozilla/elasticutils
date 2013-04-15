from nose.tools import eq_

from elasticutils.contrib.django import S, F, InvalidFieldActionError
from elasticutils.contrib.django.tests import FakeDjangoMappingType, FakeModel
from elasticutils.contrib.django.estestcase import ESTestCase
from elasticutils.tests import facet_counts_dict


class QueryTest(ESTestCase):
    @classmethod
    def setUpClass(cls):
        super(QueryTest, cls).setUpClass()

        if cls.skip_tests:
            return

        index = FakeDjangoMappingType.get_index()
        doctype = FakeDjangoMappingType.get_mapping_type_name()

        cls.create_index(index)

        data = [
            {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
            {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
            {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
            {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
            {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
            ]
        cls.index_data(data, index=index, doctype=doctype)

        # Generate all the FakeModels in our "database"
        for args in data:
            FakeModel(**args)

        cls.refresh(index)

    def test_q(self):
        eq_(len(S(FakeDjangoMappingType).query(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).query(foo='car')), 2)

    def test_q_all(self):
        eq_(len(S(FakeDjangoMappingType)), 5)

    def test_filter_empty_f(self):
        eq_(len(S(FakeDjangoMappingType).filter(F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() | F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F())), 5)

    def test_filter(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome')), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome'))), 3)

    def test_filter_and(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome', foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') & F(foo='bar'))), 1)

    def test_filter_or(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat'))), 4)

    def test_filter_or_3(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat') |
                                     F(tag='boring'))), 5)
        eq_(len(S(FakeDjangoMappingType).filter(or_={'foo': 'bar',
                                          'or_': {'tag': 'boat',
                                                  'width': '5'}
                                          })), 3)

    def test_filter_complicated(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    def test_filter_not(self):
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='awesome'))), 2)
        eq_(len(S(FakeDjangoMappingType).filter(~(F(tag='boring') | F(tag='boat')))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat')).filter(~F(foo='bar'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat', foo='barf'))), 5)

    def test_filter_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(S(FakeDjangoMappingType).filter(F(tag__faux='awesome')))

    def test_facet(self):
        qs = S(FakeDjangoMappingType).facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    def test_filtered_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    def test_global_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_facet_raw(self):
        qs = S(FakeDjangoMappingType).facet_raw(tags={'terms': {'field': 'tag'}})
        eq_(facet_counts_dict(qs, 'tags'),
            dict(awesome=3, boring=1, boat=1))

        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet_raw(tags={'terms': {'field': 'tag'}}))
        eq_(facet_counts_dict(qs, 'tags'),
            {'awesome': 2})

    def test_facet_raw_overrides_facet(self):
        """facet_raw overrides facet with the same facet name."""
        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_order_by(self):
        res = S(FakeDjangoMappingType).filter(tag='awesome').order_by('-width')
        eq_([d.id for d in res], [5, 3, 1])
