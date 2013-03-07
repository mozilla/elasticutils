from datetime import datetime, timedelta

from nose.tools import eq_

from elasticutils import F, InvalidFieldActionError, InvalidFacetType
from elasticutils.tests import ElasticTestCase, facet_counts_dict


class QueryTest(ElasticTestCase):
    @classmethod
    def setup_class(cls):
        super(QueryTest, cls).setup_class()
        if cls.skip_tests:
            return

        cls.create_index()
        cls.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
            ])
        cls.refresh()

    def test_q(self):
        eq_(len(self.get_s().query(foo='bar')), 1)
        eq_(len(self.get_s().query(foo='car')), 2)

    def test_q_all(self):
        eq_(len(self.get_s()), 5)

    def test_q_term(self):
        eq_(len(self.get_s().query(foo='car')), 2)
        eq_(len(self.get_s().query(foo__term='car')), 2)

    def test_q_in(self):
        eq_(len(self.get_s().query(foo__in=['car', 'bar'])), 3)

    def test_q_text(self):
        eq_(len(self.get_s().query(foo__text='car')), 2)

    def test_q_prefix(self):
        eq_(len(self.get_s().query(foo__prefix='ca')), 2)
        eq_(len(self.get_s().query(foo__startswith='ca')), 2)

    def test_q_text_phrase(self):
        # Doing a text query for the two words in either order kicks up
        # two results.
        eq_(len(self.get_s().query(foo__text='train car')), 2)
        eq_(len(self.get_s().query(foo__text='car train')), 2)

        # Doing a text_phrase query for the two words in the right order
        # kicks up one result.
        eq_(len(self.get_s().query(foo__text_phrase='train car')), 1)

        # Doing a text_phrase query for the two words in the wrong order
        # kicks up no results.
        eq_(len(self.get_s().query(foo__text_phrase='car train')), 0)

    def test_q_fuzzy(self):
        # Mispelled word gets no results with text query.
        eq_(len(self.get_s().query(foo__text='tran')), 0)

        # Mispelled word gets one result with fuzzy query.
        eq_(len(self.get_s().query(foo__fuzzy='tran')), 1)

    def test_q_demote(self):
        s = self.get_s().query(foo__text='car')
        scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        s = s.demote(0.5, width__term='5')
        demoted_scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        # These are both sorted by scores. We're demoting one result
        # so the top result in each list is different.
        assert scores[0] != demoted_scores

    def test_q_query_string(self):
        eq_(len(self.get_s().query(foo__query_string='car AND train')), 1)
        eq_(len(self.get_s().query(foo__query_string='car OR duck')), 3)

        # You can query against different fields with the query_string.
        eq_(len(self.get_s().query(foo__query_string='tag:boat OR car')), 3)

    def test_q_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(self.get_s().query(foo__foo='awesome'))

    def test_boost(self):
        """Boosted queries shouldn't raise a SearchPhaseExecutionException."""
        # Note: There isn't an assertion here--we just want to make
        # sure that it runs without throwing an exception.
        q1 = (self.get_s()
                  .boost(foo=4.0)
                  .query(foo='car', foo__text='car', foo__text_phrase='car'))
        list(q1)

    def test_boost_overrides(self):
        def _get_queries(search):
            # The stuff we want is buried in the search and it's in
            # the 'must' list where each item in the list is a dict
            # with a single key. So we extract that and put it in a
            # dict so we don't have to deal with the order of things
            # in the 'must' list.
            return dict([clause.items()[0]
                         for clause in search['query']['bool']['must']])

        q1 = self.get_s().boost(foo=4.0).query(foo='car', foo__prefix='car')
        eq_(_get_queries(q1._build_query())['term']['foo']['boost'], 4.0)
        eq_(_get_queries(q1._build_query())['prefix']['foo']['boost'], 4.0)

        q1 = q1.boost(foo=2.0)
        eq_(_get_queries(q1._build_query())['term']['foo']['boost'], 2.0)
        eq_(_get_queries(q1._build_query())['prefix']['foo']['boost'], 2.0)

        q1 = q1.boost(foo__prefix=4.0)
        eq_(_get_queries(q1._build_query())['term']['foo']['boost'], 2.0)
        eq_(_get_queries(q1._build_query())['prefix']['foo']['boost'], 4.0)

        # Note: We don't actually want to test whether the score for
        # an item goes up by adding a boost to the search because
        # boosting doesn't actually work like that. There's a
        # queryNorm factor which is 1/sqrt(boosts) which normalizes
        # the results from a query allowing you to compare
        # queries. Thus, doing a query, adding a boost and doing it
        # again doesn't increase the score for the item.
        #
        # Figured I'd mention that in case someone was looking at the
        # tests and was like, "Hey--this is missing!"

    def test_facet(self):
        qs = self.get_s().facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    def test_filtered_facet(self):
        qs = self.get_s().query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    def test_global_facet(self):
        qs = self.get_s().query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_facet_raw(self):
        qs = self.get_s().facet_raw(tags={'terms': {'field': 'tag'}})
        eq_(facet_counts_dict(qs, 'tags'),
            dict(awesome=3, boring=1, boat=1))

        qs = (self.get_s()
              .query(foo='car')
              .facet_raw(tags={'terms': {'field': 'tag'}}))
        eq_(facet_counts_dict(qs, 'tags'),
            {'awesome': 2})

    def test_facet_raw_overrides_facet(self):
        """facet_raw overrides facet with the same facet name."""
        qs = (self.get_s()
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_order_by(self):
        res = self.get_s().filter(tag='awesome').order_by('-width')
        eq_([d['id'] for d in res], [5, 3, 1])

    def test_repr(self):
        res = self.get_s()[:2]
        list_ = list(res)

        eq_(repr(list_), repr(res))

    def test_explain(self):
        qs = self.get_s().query(foo='car')

        assert 'explain' not in qs._build_query()

        qs = qs.explain(True)

        # You put the explain in...
        assert qs._build_query()['explain'] == True

        qs = qs.explain(False)

        # You take the explain out...
        assert 'explain' not in qs._build_query()

        # Shake it all about...
        qs = qs.explain(True)

        res = list(qs)
        assert res[0]._explanation

    def test_highlight_with_dict_results(self):
        """Make sure highlighting with dict-style results works.

        Highlighting should work on all fields specified in the ``highlight()``
        call, not just the ones mentioned in the query or in ``values_dict()``.

        """
        s = (self.get_s().query(foo__text='car')
                         .filter(id=5)
                         .highlight('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result._highlight['foo'], [u'train <em>car</em>'])

        s = (self.get_s().query(foo__text='car')
                         .filter(id=5)
                         .highlight('tag', 'foo')
                         .values_dict('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result._highlight['foo'], [u'train <em>car</em>'])

    def test_highlight_on_list_results(self):
        """Make sure highlighting with list-style results works.

        Highlighting should work on all fields specified in the ``highlight()``
        call, not just the ones mentioned in the query or in ``values_list()``.

        """
        s = (self.get_s().query(foo__text='car')
                         .filter(id=5)
                         .highlight('tag', 'foo')
                         .values_list('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result._highlight['foo'], [u'train <em>car</em>'])

    def test_highlight_options(self):
        """Make sure highlighting with options works."""
        s = (self.get_s().query(foo__text='car')
                         .filter(id=5)
                         .highlight('tag', 'foo',
                                    pre_tags=['<b>'],
                                    post_tags=['</b>']))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result._highlight['foo'], [u'train <b>car</b>'])

    def test_highlight_cumulative(self):
        """Make sure highlighting fields are cumulative and none clears them."""
        # No highlighted fields means no highlights.
        s = (self.get_s().query(foo__text='car')
                         .filter(id=5)
                         .highlight())
        eq_(list(s)[0]._highlight, {})

        # Add a field and that gets highlighted.
        s = s.highlight('foo')
        eq_(list(s)[0]._highlight['foo'], [u'train <em>car</em>'])

        # Set it back to no fields and no highlight.
        s = s.highlight(None)
        eq_(list(s)[0]._highlight, {})


class FilterTest(ElasticTestCase):
    @classmethod
    def setup_class(cls):
        super(FilterTest, cls).setup_class()
        if cls.skip_tests:
            return

        cls.create_index(settings={
                'mappings': {
                    ElasticTestCase.mapping_type_name: {
                        'properties': {
                            'id': {'type': 'integer'},
                            'foo': {'type': 'string'},
                            'tag': {'type': 'string'},
                            'width': {'type': 'string', 'null_value': True}
                            }
                        }
                    }
                })

        cls.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'},
                {'id': 6, 'foo': 'caboose', 'tag': 'end', 'width': None}
            ])
        cls.refresh()

    def test_filter_empty_f(self):
        eq_(len(self.get_s().filter(F() | F(tag='awesome'))), 3)
        eq_(len(self.get_s().filter(F() & F(tag='awesome'))), 3)
        eq_(len(self.get_s().filter(F() | F() | F(tag='awesome'))), 3)
        eq_(len(self.get_s().filter(F() & F() & F(tag='awesome'))), 3)
        eq_(len(self.get_s().filter(F())), 6)

    def test_filter(self):
        eq_(len(self.get_s().filter(tag='awesome')), 3)
        eq_(len(self.get_s().filter(F(tag='awesome'))), 3)

    def test_filter_and(self):
        eq_(len(self.get_s().filter(tag='awesome', foo='bar')), 1)
        eq_(len(self.get_s().filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(self.get_s().filter(F(tag='awesome') & F(foo='bar'))), 1)

    def test_filter_or(self):
        eq_(len(self.get_s().filter(F(tag='awesome') | F(tag='boat'))), 4)

    def test_filter_or_3(self):
        eq_(len(self.get_s().filter(F(tag='awesome') | F(tag='boat') |
                                     F(tag='boring'))), 5)
        eq_(len(self.get_s().filter(or_={'foo': 'bar',
                                          'or_': {'tag': 'boat',
                                                  'width': '5'}
                                          })), 3)

    def test_filter_complicated(self):
        eq_(len(self.get_s().filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    def test_filter_not(self):
        eq_(len(self.get_s().filter(~F(tag='awesome'))), 3)
        eq_(len(self.get_s().filter(~(F(tag='boring') | F(tag='boat')))), 4)
        eq_(len(self.get_s().filter(~F(tag='boat')).filter(~F(foo='bar'))), 4)
        eq_(len(self.get_s().filter(~F(tag='boat', foo='barf'))), 6)

    def test_filter_in(self):
        eq_(len(self.get_s().filter(foo__in=['car', 'bar'])), 3)

    def test_filter_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(self.get_s().filter(F(tag__faux='awesome')))

    def test_filter_on_none(self):
        eq_(len(self.get_s().filter(width=None)), 1)

    def test_f_mutation_with_and(self):
        """Make sure AND doesn't mutate operands."""
        f1 = F(fielda='tag', fieldb='boat')
        f2 = F(fieldc='car')

        f1 & f2
        # Should only contain f1 filters.
        eq_(sorted(f1.filters['and']),
            sorted([{'term': {'fielda': 'tag'}},
                    {'term': {'fieldb': 'boat'}}]))

        # Should only contain f2 filters.
        eq_(f2.filters, {'term': {'fieldc': 'car'}})

    def test_f_mutation_with_or(self):
        """Make sure OR doesn't mutate operands."""
        f1 = F(fielda='tag', fieldb='boat')
        f2 = F(fieldc='car')

        f1 | f2
        # Should only contain f1 filters.
        eq_(sorted(f1.filters['and']),
            sorted([{'term': {'fielda': 'tag'}},
                    {'term': {'fieldb': 'boat'}}]))

        # Should only contain f2 filters.
        eq_(f2.filters, {'term': {'fieldc': 'car'}})

    def test_f_mutation_with_not(self):
        """Make sure NOT doesn't mutate operands."""
        f1 = F(fielda='tag')
        f2 = ~f1

        # Change f2 to see if it changes f1.
        f2.filters['not']['filter']['term']['fielda'] = 'boat'

        # Should only contain f1 filters.
        eq_(f1.filters, {'term': {'fielda': 'tag'}})

        # Should only contain f2 tweaked filter.
        eq_(f2.filters, {'not': {'filter': {'term': {'fielda': 'boat'}}}})


class FacetTest(ElasticTestCase):
    def test_facet_date_histogram(self):
        """facet_raw with date_histogram works."""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'created': today},
                {'id': 2, 'created': today},
                {'id': 3, 'created': tomorrow},
                {'id': 4, 'created': tomorrow},
                {'id': 5, 'created': tomorrow},
            ])
        FacetTest.refresh()

        qs = (self.get_s()
              .facet_raw(created1={
                    'date_histogram': {
                        'interval': 'day', 'field': 'created'
                        }
                    }))

        # TODO: This is a mediocre test because it doesn't test the
        # dates and it probably should.
        facet_counts = [item['count']
                        for item in qs.facet_counts()['created1']]
        eq_(sorted(facet_counts), [2, 3])

    def test_facet_date_histogram(self):
        """facet_raw with normal histogram works."""

        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'value': 1},
                {'id': 2, 'value': 1},
                {'id': 3, 'value': 1},
                {'id': 4, 'value': 2},
                {'id': 5, 'value': 2},
                {'id': 6, 'value': 3},
                {'id': 7, 'value': 3},
                {'id': 8, 'value': 3},
                {'id': 9, 'value': 4},
            ])
        FacetTest.refresh()

        qs = (self.get_s()
              .facet_raw(created1={
                    'histogram': {
                        'interval': 2, 'field': 'value'
                        }
                    }))

        data = qs.facet_counts()
        eq_(data, {
                u'created1': [
                    {u'key': 0, u'count': 3},
                    {u'key': 2, u'count': 5},
                    {u'key': 4, u'count': 1},
                ]
            })


    def test_invalid_field_type(self):
        """Invalid _type should raise InvalidFacetType."""
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'age': 30},
                {'id': 2, 'age': 40}
            ])
        FacetTest.refresh()

        # Note: This uses a statistcal facet. If we implement handling
        # for that, then we need to pick another facet type to fail on
        # or do the right thing and mock the test.
        # Note: This used to use a histogram facet, but that was
        # implemented.
        self.assertRaises(
            InvalidFacetType,
            lambda: (self.get_s()
                     .facet_raw(created1={
                        'statistical': {'field': 'age'}})
                     .facet_counts()))
