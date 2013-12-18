from datetime import datetime, timedelta
from unittest import TestCase

from nose.tools import eq_

from elasticutils import (
    S, F, Q, BadSearch, InvalidFieldActionError, InvalidFacetType,
    InvalidFlagsError, SearchResults, DefaultMappingType, MappingType,
    DEFAULT_INDEXES, DEFAULT_DOCTYPES)
from elasticutils.tests import ESTestCase, facet_counts_dict


class FakeMappingType(MappingType):
    @classmethod
    def get_index(cls):
        return 'index123'

    @classmethod
    def get_mapping_type_name(cls):
        return 'doctype123'


class STest(TestCase):
    def test_untyped_s_get_indexes(self):
        eq_(S().get_indexes(), DEFAULT_INDEXES)
        eq_(S().indexes('abc').get_indexes(), ['abc'])

    def test_typed_s_get_indexes(self):
        eq_(S(FakeMappingType).get_indexes(), ['index123'])

    def test_untyped_s_get_doctypes(self):
        eq_(S().get_doctypes(), DEFAULT_DOCTYPES)
        eq_(S().doctypes('abc').get_doctypes(), ['abc'])

    def test_typed_s_get_doctypes(self):
        eq_(S(FakeMappingType).get_doctypes(), ['doctype123'])


class QTest(TestCase):
    def test_q_should(self):
        q = Q(foo__text='abc', bar__text='def', should=True)
        eq_(sorted(q.should_q), [('bar__text', 'def'), ('foo__text', 'abc')])
        eq_(sorted(q.must_q), [])
        eq_(sorted(q.must_not_q), [])

    def test_q_must(self):
        q = Q(foo__text='abc', bar__text='def', must=True)
        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [('bar__text', 'def'), ('foo__text', 'abc')])
        eq_(sorted(q.must_not_q), [])

    def test_q_must_not(self):
        q = Q(foo__text='abc', bar__text='def', must_not=True)
        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [])
        eq_(sorted(q.must_not_q), [('bar__text', 'def'), ('foo__text', 'abc')])

    def test_q_must_should(self):
        with self.assertRaises(InvalidFlagsError):
            Q(foo__text='abc', must=True, should=True)

    def test_q_basic_add(self):
        """Adding one Q to another Q combines them."""
        q = Q(foo__text='abc') + Q(bar__text='def')

        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [('bar__text', 'def'), ('foo__text', 'abc')])
        eq_(sorted(q.must_not_q), [])

    def test_q_order(self):
        q1 = Q(foo__text='abc') + Q(bar__text='def')

        q2 = Q(bar__text='def') + Q(foo__text='abc')
        eq_(q1, q2)

        q2 = Q(bar__text='def')
        q2 += Q(foo__text='abc')
        eq_(q1, q2)

        q2 = Q(foo__text='abc')
        q2 += Q(bar__text='def')
        eq_(q1, q2)

    def test_q_mixed(self):
        q1 = Q(foo__text='should', bar__text='should', should=True)
        q2 = Q(baz='must')
        q3 = Q(bat='must_not', must_not=True)
        q4 = Q(ban='must', must=True)
        q5 = Q(bam='must', must=True)

        q_all = q1 + q2 + q3 + q4 + q5

        eq_(sorted(q_all.should_q),
            [('bar__text', 'should'), ('foo__text', 'should')])

        eq_(sorted(q_all.must_q),
            [('bam', 'must'), ('ban', 'must'), ('baz', 'must')])

        eq_(sorted(q_all.must_not_q),
            [('bat', 'must_not')])


class QueryTest(ESTestCase):
    data = [
        {
            'id': 1,
            'foo': 'bar',
            'tag': 'awesome',
            'width': '2',
            'height': 7
        },
        {
            'id': 2,
            'foo': 'bart',
            'tag': 'boring',
            'width': '7',
            'height': 11
        },
        {
            'id': 3,
            'foo': 'car',
            'tag': 'awesome',
            'width': '5',
            'height': 5
        },
        {
            'id': 4,
            'foo': 'duck',
            'tag': 'boat',
            'width': '11',
            'height': 7
        },
        {
            'id': 5,
            'foo': 'train car',
            'tag': 'awesome',
            'width': '7',
            'height': 2
        }
    ]

    def test_q_all(self):
        eq_(len(self.get_s()), 5)

    def test_q(self):
        eq_(len(self.get_s().query(foo='bar')), 1)
        eq_(len(self.get_s().query(foo='car')), 2)

        eq_(len(self.get_s().query(Q(foo='bar'))), 1)
        eq_(len(self.get_s().query(Q(foo='car'))), 2)

    def test_q_term(self):
        eq_(len(self.get_s().query(foo='car')), 2)
        eq_(len(self.get_s().query(foo__term='car')), 2)

        eq_(len(self.get_s().query(Q(foo='car'))), 2)
        eq_(len(self.get_s().query(Q(foo__term='car'))), 2)

    def test_q_terms(self):
        eq_(len(self.get_s().query(foo__terms=['car', 'duck'])), 3)

        eq_(len(self.get_s().query(Q(foo__terms=['car', 'duck']))), 3)

    def test_q_in(self):
        eq_(len(self.get_s().query(foo__in=['car', 'bar'])), 3)

        eq_(len(self.get_s().query(Q(foo__in=['car', 'bar']))), 3)

    def test_q_range(self):
        eq_(len(self.get_s().query(height__gt=10)), 1)
        eq_(len(self.get_s().query(height__gte=7)), 3)
        eq_(len(self.get_s().query(height__lt=10)), 4)
        eq_(len(self.get_s().query(height__lte=7)), 4)

        eq_(len(self.get_s().query(Q(height__gt=10))), 1)
        eq_(len(self.get_s().query(Q(height__gte=7))), 3)
        eq_(len(self.get_s().query(Q(height__lt=10))), 4)
        eq_(len(self.get_s().query(Q(height__lte=7))), 4)

    def test_q_range_action(self):
        eq_(len(self.get_s().query(height__range=(10, 20))), 1)
        eq_(len(self.get_s().query(height__range=(0, 7))), 4)
        eq_(len(self.get_s().query(height__range=(5, 7))), 3)

        eq_(len(self.get_s().query(Q(height__range=(10, 20)))), 1)
        eq_(len(self.get_s().query(Q(height__range=(0, 7)))), 4)
        eq_(len(self.get_s().query(Q(height__range=(5, 7)))), 3)

        # Try a boosted query to verify it still works.
        eq_(len(self.get_s().query(height__range=(5, 7))
                            .boost(height__range=100)), 3)

    def test_q_text(self):
        eq_(len(self.get_s().query(foo__text='car')), 2)

        eq_(len(self.get_s().query(Q(foo__text='car'))), 2)

    def test_q_match(self):
        eq_(len(self.get_s().query(foo__match='car')), 2)

        eq_(len(self.get_s().query(Q(foo__match='car'))), 2)

    def test_q_prefix(self):
        eq_(len(self.get_s().query(foo__prefix='ca')), 2)
        eq_(len(self.get_s().query(foo__startswith='ca')), 2)

        eq_(len(self.get_s().query(Q(foo__prefix='ca'))), 2)
        eq_(len(self.get_s().query(Q(foo__startswith='ca'))), 2)

    def test_q_text_phrase(self):
        # Doing a text query for the two words in either order kicks up
        # two results.
        eq_(len(self.get_s().query(foo__text='train car')), 2)
        eq_(len(self.get_s().query(foo__text='car train')), 2)

        eq_(len(self.get_s().query(Q(foo__text='train car'))), 2)
        eq_(len(self.get_s().query(Q(foo__text='car train'))), 2)

        # Doing a text_phrase query for the two words in the right order
        # kicks up one result.
        eq_(len(self.get_s().query(foo__text_phrase='train car')), 1)

        eq_(len(self.get_s().query(Q(foo__text_phrase='train car'))), 1)

        # Doing a text_phrase query for the two words in the wrong order
        # kicks up no results.
        eq_(len(self.get_s().query(foo__text_phrase='car train')), 0)

        eq_(len(self.get_s().query(Q(foo__text_phrase='car train'))), 0)

    def test_q_match_phrase(self):
        # Doing a match query for the two words in either order kicks up
        # two results.
        eq_(len(self.get_s().query(foo__match='train car')), 2)
        eq_(len(self.get_s().query(foo__match='car train')), 2)

        eq_(len(self.get_s().query(Q(foo__match='train car'))), 2)
        eq_(len(self.get_s().query(Q(foo__match='car train'))), 2)

        # Doing a match_phrase query for the two words in the right
        # order kicks up one result.
        eq_(len(self.get_s().query(foo__match_phrase='train car')), 1)

        eq_(len(self.get_s().query(Q(foo__match_phrase='train car'))), 1)

        # Doing a match_phrase query for the two words in the wrong
        # order kicks up no results.
        eq_(len(self.get_s().query(foo__match_phrase='car train')), 0)

        eq_(len(self.get_s().query(Q(foo__match_phrase='car train'))), 0)

    def test_q_fuzzy(self):
        # Mispelled word gets no results with text query.
        eq_(len(self.get_s().query(foo__text='tran')), 0)

        eq_(len(self.get_s().query(Q(foo__text='tran'))), 0)

        # Mispelled word gets one result with fuzzy query.
        eq_(len(self.get_s().query(foo__fuzzy='tran')), 1)

        eq_(len(self.get_s().query(Q(foo__fuzzy='tran'))), 1)

    def test_q_wildcard(self):
        eq_(len(self.get_s().query(foo__wildcard='tra*n')), 1)
        eq_(len(self.get_s().query(foo__wildcard='tra?n')), 1)

        eq_(len(self.get_s().query(Q(foo__wildcard='tra*n'))), 1)
        eq_(len(self.get_s().query(Q(foo__wildcard='tra?n'))), 1)

    def test_q_demote(self):
        s = self.get_s().query(foo__text='car')
        scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        s = s.demote(0.5, width__term='5')
        demoted_scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        # These are both sorted by scores. We're demoting one result
        # so the top result in each list is different.
        assert scores[0] != demoted_scores

        # Now we do the whole thing again with Qs.
        s = self.get_s().query(Q(foo__text='car'))
        scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        s = s.demote(0.5, Q(width__term='5'))
        demoted_scores = [(sr['id'], sr._score) for sr in s.values_dict('id')]

        # These are both sorted by scores. We're demoting one result
        # so the top result in each list is different.
        assert scores[0] != demoted_scores

    def test_q_query_string(self):
        eq_(len(self.get_s().query(foo__query_string='car AND train')), 1)
        eq_(len(self.get_s().query(foo__query_string='car OR duck')), 3)

        eq_(len(self.get_s().query(Q(foo__query_string='car AND train'))), 1)
        eq_(len(self.get_s().query(Q(foo__query_string='car OR duck'))), 3)

        # You can query against different fields with the query_string.
        eq_(len(self.get_s().query(foo__query_string='tag:boat OR car')), 3)

        eq_(len(self.get_s().query(Q(foo__query_string='tag:boat OR car'))), 3)

    def test_q_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(self.get_s().query(foo__foo='awesome'))

        with self.assertRaises(InvalidFieldActionError):
            len(self.get_s().query(Q(foo__foo='awesome')))

    def test_deprecated_q_or_(self):
        s = self.get_s().query(or_={'foo': 'car', 'tag': 'boat'})
        eq_(s._build_query(),
            {
                'query': {
                    'bool': {
                        'should': [
                            {'term': {'foo': 'car'}},
                            {'term': {'tag': 'boat'}}
                        ]
                    }
                }
            }
        )

    def test_bad_search(self):
        with self.assertRaises(BadSearch):
            len(S().doctypes('abc'))

    def test_query_raw(self):
        s = self.get_s().query_raw({'match': {'title': 'example'}})
        eq_(s._build_query(),
            {'query': {'match': {'title': 'example'}}})

    def test_query_raw_overrides_everything(self):
        s = self.get_s().query_raw({'match': {'title': 'example'}})
        s = s.query(foo__text='foo')
        s = s.demote(0.5, title__text='bar')
        s = s.boost(title=5.0)

        eq_(s._build_query(),
            {'query': {'match': {'title': 'example'}}})

    def test_boost(self):
        """Boosted queries shouldn't raise a SearchPhaseExecutionException."""
        q1 = (self.get_s()
                  .boost(foo=4.0)
                  .query(foo='car', foo__text='car', foo__text_phrase='car'))

        # Make sure the query executes without throwing an exception.
        list(q1)

        # Verify it's producing the correct query.
        eq_(q1._build_query(),
            {
                'query': {
                    'bool': {
                        'must': [
                            {'text_phrase': {'foo': {'query': 'car', 'boost': 4.0}}},
                            {'term': {'foo': {'value': 'car', 'boost': 4.0}}},
                            {'text': {'foo': {'query': 'car', 'boost': 4.0}}}
                        ]
                    }
                }
            })

        # Do the same thing with Qs.
        q1 = (self.get_s()
                  .boost(foo=4.0)
                  .query(Q(foo='car', foo__text='car', foo__text_phrase='car')))

        # Make sure the query executes without throwing an exception.
        list(q1)

        # Verify it's producing the correct query.
        eq_(q1._build_query(),
            {
                'query': {
                    'bool': {
                        'must': [
                            {'text_phrase': {'foo': {'query': 'car', 'boost': 4.0}}},
                            {'term': {'foo': {'value': 'car', 'boost': 4.0}}},
                            {'text': {'foo': {'query': 'car', 'boost': 4.0}}}
                        ]
                    }
                }
            })

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

    def test_boolean_query_compled(self):
        """Verify that should/must/must_not collapses right"""
        s = self.get_s()

        eq_((s.query(Q(foo='should', should=True),
                     bar='must')
             ._build_query()),
            {
                'query': {
                    'bool': {
                        'should': [
                            {'term': {'foo': 'should'}}
                        ],
                        'must': [
                            {'term': {'bar': 'must'}}
                        ]
                    }
                }
            })

        eq_((s.query(Q(foo='should', should=True),
                     bar='must_not', must_not=True)
             ._build_query()),
            {
                'query': {
                    'bool': {
                        'should': [
                            {'term': {'foo': 'should'}}
                        ],
                        'must_not': [
                            {'term': {'bar': 'must_not'}}
                        ]
                    }
                }
            })

        eq_((s.query(Q(foo='should', should=True),
                     bar='must_not', must_not=True)
             .query(Q(baz='must'))
             ._build_query()),
            {
                'query': {
                    'bool': {
                        'should': [
                            {'term': {'foo': 'should'}},
                        ],
                        'must_not': [
                            {'term': {'bar': 'must_not'}}
                        ],
                        'must': [
                            {'term': {'baz': 'must'}}
                        ]
                    }
                }
            })

        # This is a pathological case. The should=True applies to the
        # foo term query and the must=True doesn't apply to
        # anything--it shouldn't override the should=True in the Q.
        eq_((s.query(Q(foo='should', should=True), must=True)
             ._build_query()),
            {
                'query': {
                    'bool': {
                        'should': [
                            {'term': {'foo': 'should'}}
                        ]
                    }
                }
            })

    def test_funkyquery(self):
        """Test implementing query processors"""
        class FunkyS(S):
            def process_query_funkyquery(self, key, val, field_action):
                return {'funkyquery': {'field': key, 'value': val}}

        s = FunkyS().query(foo__funkyquery='bar')
        eq_(s._build_query(),
            {
                'query': {
                    'funkyquery': {'field': 'foo', 'value': 'bar'}
                }
            })

    def test_execute(self):
        s = self.get_s()
        results = s.execute()
        assert isinstance(results, SearchResults)

        cached = s.execute()
        assert cached is results

        # Test caching of empty results
        try:
            self.teardown_class()
            self.create_index(settings={'mappings': self.mapping})
            self.refresh()

            s = self.get_s()
            results = s.execute()
            assert isinstance(results, SearchResults)

            cached = s.execute()
            assert cached is results
        finally:
            self.setup_class()

    def test_count(self):
        s = self.get_s()
        assert isinstance(s.count(), int)

        # Make sure it works with the cached count
        s.execute()
        assert isinstance(s.count(), int)

    def test_len(self):
        assert isinstance(len(self.get_s()), int)

    def test_all(self):
        assert isinstance(self.get_s().all(), SearchResults)

    def test_order_by(self):
        res = self.get_s().filter(tag='awesome').order_by('-width')
        eq_([d['id'] for d in res], [5, 3, 1])

    def test_order_by_dict(self):
        res = self.get_s().filter(tag='awesome').order_by({'width': 'desc'})
        eq_([d['id'] for d in res], [5, 3, 1])

    def test_slice(self):
        s = self.get_s().filter(tag='awesome')
        eq_(s._build_query(),
            {'filter': {'term': {'tag': 'awesome'}}})
        assert isinstance(s[0], DefaultMappingType)

        eq_(s[0:1]._build_query(),
            {'filter': {'term': {'tag': 'awesome'}}, 'size': 1})

        eq_(s[1:2]._build_query(),
            {'filter': {'term': {'tag': 'awesome'}}, 'from': 1, 'size': 1})

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


class FilterTest(ESTestCase):
    mapping = {
        ESTestCase.mapping_type_name: {
            'properties': {
                'id': {'type': 'integer'},
                'foo': {'type': 'string'},
                'tag': {'type': 'string'},
                'width': {'type': 'string', 'null_value': True}
                }
            }
        }

    data = [
        {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
        {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
        {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
        {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
        {'id': 5, 'foo': 'car', 'tag': 'awesome', 'width': '7'},
        {'id': 6, 'foo': 'caboose', 'tag': 'end', 'width': None}
        ]

    def test_filter_empty_f(self):
        s = self.get_s().filter(F())
        eq_(s._build_query(), {})
        eq_(s.count(), 6)

    def test_filter_empty_f_or_f(self):
        s = self.get_s().filter(F() | F(tag='awesome'))
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_and_f(self):
        s = self.get_s().filter(F() & F(tag='awesome'))
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_f_and_empty_f(self):
        s = self.get_s().filter(F(tag='awesome') & F())
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_f_and_ff(self):
        s = self.get_s().filter(F(tag='awesome') & F(foo='car', width='7'))
        eq_(s._build_query(),
            {
                'filter': {
                    'and': [
                        {'term': {'width': '7'}},
                        {'term': {'foo': 'car'}},
                        {'term': {'tag': 'awesome'}}
                    ]
                }
            }
        )
        eq_(s.count(), 1)

    def test_filter_empty_f_or_empty_f_or_f(self):
        s = self.get_s().filter(F() | F() | F(tag='awesome'))
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_and_empty_f_and_f(self):
        s = self.get_s().filter(F() & F() & F(tag='awesome'))
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_not_not_f(self):
        f = F(tag='awesome')
        f = ~f
        f = ~f
        s = self.get_s().filter(f)
        eq_(s._build_query(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_not(self):
        s = self.get_s().filter(~F())
        eq_(s._build_query(), {})
        eq_(s.count(), 6)

    def test_filter(self):
        eq_(len(self.get_s().filter(tag='awesome')), 3)
        eq_(len(self.get_s().filter(F(tag='awesome'))), 3)

    def test_filter_and(self):
        eq_(len(self.get_s().filter(tag='awesome', foo='bar')), 1)
        eq_(len(self.get_s().filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(self.get_s().filter(F(tag='awesome') & F(foo='bar'))), 1)

    def test_filter_or(self):
        s = self.get_s().filter(F(tag='awesome') | F(tag='boat'))
        eq_(s.count(), 4)

    def test_filter_or_3(self):
        s = self.get_s().filter(F(tag='awesome') | F(tag='boat') |
                                F(tag='boring'))
        eq_(s._build_query(), {
                'filter': {
                    'or': [
                        {'term': {'tag': 'awesome'}},
                        {'term': {'tag': 'boat'}},
                        {'term': {'tag': 'boring'}}
                    ]
                }
        })
        eq_(s.count(), 5)

        # This is kind of a crazy case.
        s = self.get_s().filter(or_={'foo': 'bar',
                                     'or_': {'tag': 'boat', 'width': '5'}})
        eq_(s._build_query(), {
                'filter': {
                    'or': [
                        {'or': [
                                {'term': {'width': '5'}},
                                {'term': {'tag': 'boat'}}
                        ]},
                        {'term': {'foo': 'bar'}}
                    ]
                }
        })
        eq_(s.count(), 3)

    def test_filter_complicated(self):
        eq_(len(self.get_s().filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    def test_filter_not(self):
        s = self.get_s().filter(~F(tag='awesome'))
        eq_(s._build_query(), {
                'filter': {
                    'not': {
                        'filter': {'term': {'tag': 'awesome'}}
                    }
                }
        })
        eq_(s.count(), 3)

        s = self.get_s().filter(~(F(tag='boring') | F(tag='boat')))
        eq_(s._build_query(), {
                'filter': {
                    'not': {
                        'filter': {
                            'or': [
                                {'term': {'tag': 'boring'}},
                                {'term': {'tag': 'boat'}}
                            ]
                        }
                    }
                }
        })
        eq_(s.count(), 4)

        s = self.get_s().filter(~F(tag='boat')).filter(~F(foo='bar'))
        eq_(s._build_query(), {
                'filter': {
                    'and': [
                        {'not': {'filter': {'term': {'tag': 'boat'}}}},
                        {'not': {'filter': {'term': {'foo': 'bar'}}}}
                    ]
                }
        })
        eq_(s.count(), 4)

        s = self.get_s().filter(~F(tag='boat', foo='barf'))
        eq_(s._build_query(), {
                'filter': {
                    'not': {
                        'filter': {
                            'and': [
                                {'term': {'foo': 'barf'}},
                                {'term': {'tag': 'boat'}}
                            ]
                        }
                    }
                }
        })
        eq_(s.count(), 6)

    def test_filter_in(self):
        eq_(len(self.get_s().filter(foo__in=['car', 'bar'])), 3)

    def test_filter_prefix(self):
        eq_(len(self.get_s().filter(foo__prefix='c')), 3)

    def test_filter_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(self.get_s().filter(F(tag__faux='awesome')))

    def test_filter_with_none_value(self):
        eq_(len(self.get_s().filter(width=None)), 1)

    def test_f_mutation_with_and(self):
        """Make sure AND doesn't mutate operands."""
        f1 = F(fielda='tag', fieldb='boat')
        f2 = F(fieldc='car')

        f1 & f2
        # Should only contain f1 filters.
        eq_(sorted(f1.filters[0]['and']),
            sorted([('fielda', 'tag'), ('fieldb', 'boat')]))

        # Should only contain f2 filters.
        eq_(f2.filters, [('fieldc', 'car')])

    def test_f_mutation_with_or(self):
        """Make sure OR doesn't mutate operands."""
        f1 = F(fielda='tag', fieldb='boat')
        f2 = F(fieldc='car')

        f1 | f2
        # Should only contain f1 filters.
        eq_(sorted(f1.filters[0]['and']),
            sorted([('fielda', 'tag'), ('fieldb', 'boat')]))

        # Should only contain f2 filters.
        eq_(f2.filters, [('fieldc', 'car')])

    def test_f_mutation_with_not(self):
        """Make sure NOT doesn't mutate operands."""
        f1 = F(fielda='tag')
        f2 = ~f1

        # Change f2 to see if it changes f1.
        f2.filters[0]['not']['filter'] = [('fielda', 'boat')]

        # Should only contain f1 filters.
        eq_(f1.filters, [('fielda', 'tag')])

        # Should only contain f2 tweaked filter.
        eq_(f2.filters, [{'not': {'filter': [('fielda', 'boat')]}}])

    def test_funkyfilter(self):
        """Test implementing filter processors"""
        class FunkyS(S):
            def process_filter_funkyfilter(self, key, val, field_action):
                return {'funkyfilter': {'field': key, 'value': val}}

        s = FunkyS().filter(foo__funkyfilter='bar')
        eq_(s._build_query(), {
                'filter': {
                    'funkyfilter': {'field': 'foo', 'value': 'bar'}
                }
        })

    def test_filter_range(self):
        eq_(len(self.get_s().filter(id__gt=3)), 3)
        eq_(len(self.get_s().filter(id__gte=3)), 4)
        eq_(len(self.get_s().filter(id__lt=3)), 2)
        eq_(len(self.get_s().filter(id__lte=3)), 3)


    def test_filter_range_action(self):
        eq_(len(self.get_s().filter(id__range=(3, 10))), 4)
        eq_(len(self.get_s().filter(id__range=(0, 3))), 3)

    def test_filter_raw(self):
        s = self.get_s().filter_raw({'term': {'tag': 'awesome'}})
        eq_(s._build_query(),
            {'filter': {'term': {'tag': 'awesome'}}})

    def test_filter_raw_overrides_everything(self):
        s = self.get_s().filter_raw({'term': {'tag': 'awesome'}})
        s = s.filter(tag='boring')
        s = s.filter(F(tag='end'))
        eq_(s._build_query(),
            {'filter': {'term': {'tag': 'awesome'}}})


class FacetTest(ESTestCase):
    def test_facet(self):
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome'},
            ])
        FacetTest.refresh()

        qs = self.get_s().facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    def test_filtered_facet(self):
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': 1},
                {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': 2},
                {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': 1},
                {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': 5},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': 5},
            ])
        FacetTest.refresh()

        qs = self.get_s().query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    def test_global_facet(self):
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome'}
            ])
        FacetTest.refresh()

        qs = self.get_s().query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_facet_raw(self):
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome'}
            ])
        FacetTest.refresh()

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
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome'}
            ])
        FacetTest.refresh()

        qs = (self.get_s()
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    def test_facet_terms(self):
        """Test terms facet"""
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'color': 'red'},
                {'id': 2, 'color': 'red'},
                {'id': 3, 'color': 'red'},
                {'id': 4, 'color': 'yellow'},
                {'id': 5, 'color': 'yellow'},
                {'id': 6, 'color': 'green'},
                {'id': 7, 'color': 'blue'},
                {'id': 8, 'color': 'white'},
                {'id': 9, 'color': 'brown'},
            ])
        FacetTest.refresh()

        qs = (self.get_s()
              .facet_raw(created1={
                    'terms': {
                        'field': 'color',
                        'size': 2
                    }
              })
        )

        data = qs.facet_counts()
        eq_(data,
            {
                u'created1': [
                    {u'count': 3, u'term': u'red'},
                    {u'count': 2, u'term': u'yellow'}
                ]
            }
        )

    def test_facet_range(self):
        """Test range facet"""
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
                    'range': {
                        'field': 'value',
                        'ranges': [
                            {'from': 0, 'to': 5},
                            {'from': 5, 'to': 20}
                        ]
                    }
              }
              )
        )

        data = qs.facet_counts()
        eq_(data,
            {
                u'created1': [
                    {u'count': 9, u'from': 0.0, u'min': 1.0, u'max': 4.0,
                     u'to': 5.0, u'total_count': 9, u'total': 20.0,
                     u'mean': 2.2222222222222223},
                    {u'count': 0, u'from': 5.0, u'total_count': 0,
                     u'to': 20.0, u'total': 0.0, u'mean': 0.0}
                ]
            }
        )

    def test_facet_histogram(self):
        """Test histogram facet"""
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

    def test_facet_statistical(self):
        """Test statistical facet"""
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
                    'statistical': {
                        'field': 'value'
                    }
              })
        )

        data = qs.facet_counts()
        eq_(data,
            {
                u'created1': {
                    u'count': 9,
                    u'_type': u'statistical',
                    u'min': 1.0,
                    u'sum_of_squares': 54.0,
                    u'max': 4.0,
                    u'std_deviation': 1.0304020550550783,
                    u'variance': 1.0617283950617287,
                    u'total': 20.0,
                    u'mean': 2.2222222222222223
                }
            }
        )

    def test_filter_facet(self):
        """Test filter facet"""
        FacetTest.create_index()
        FacetTest.index_data([
            {'id': 1, 'color': 'red'},
            {'id': 2, 'color': 'red'},
            {'id': 3, 'color': 'red'},
            {'id': 4, 'color': 'yellow'},
            {'id': 5, 'color': 'yellow'},
            {'id': 6, 'color': 'green'},
            {'id': 7, 'color': 'blue'},
            {'id': 8, 'color': 'white'},
            {'id': 9, 'color': 'brown'},
        ])
        FacetTest.refresh()

        red_or_yellow_filter = {
            'filter': {
                'or': [
                    {'term': {'color': 'red'}},
                    {'term': {'color': 'yellow'}},
                ]
            }
        }
        qs = (self.get_s().facet_raw(red_or_yellow=red_or_yellow_filter))

        data = qs.facet_counts()
        eq_(data, {'red_or_yellow': {u'_type': 'filter', u'count': 5}})

    def test_query_facet(self):
        """Test query facet"""
        FacetTest.create_index()
        FacetTest.index_data([
            {'id': 1, 'color': 'red'},
            {'id': 2, 'color': 'red'},
            {'id': 3, 'color': 'red'},
            {'id': 4, 'color': 'yellow'},
            {'id': 5, 'color': 'yellow'},
            {'id': 6, 'color': 'green'},
            {'id': 7, 'color': 'blue'},
            {'id': 8, 'color': 'white'},
            {'id': 9, 'color': 'brown'},
        ])
        FacetTest.refresh()

        red_query = {
            'query': {
                'term': {'color': 'red'},
            }
        }
        qs = (self.get_s().facet_raw(red_query=red_query))

        data = qs.facet_counts()
        eq_(data, {'red_query': {u'_type': 'query', u'count': 3}})

    def test_invalid_field_type(self):
        """Invalid _type should raise InvalidFacetType."""
        FacetTest.create_index()
        FacetTest.index_data([
                {'id': 1, 'age': 30},
                {'id': 2, 'age': 40}
            ])
        FacetTest.refresh()

        # Note: This uses a terms_stats facet. If we implement handling
        # for that, then we need to pick another facet type to fail on
        # or do the right thing and mock the test.
        # Note: Previously this used histogram and statistical facets,
        # but those were implemented.
        with self.assertRaises(InvalidFacetType):
            (self.get_s()
                 .facet_raw(created1={'terms_stats': {'key_field': 'age',
                                                      'value_field': 'age'}})
                 .facet_counts())


class HighlightTest(ESTestCase):
    @classmethod
    def setup_class(cls):
        super(HighlightTest, cls).setup_class()
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


def test_to_python():
    def check_to_python(obj, expected):
        eq_(S().to_python(obj), expected)

    tests = [
        (
            {'date': '2013-05-15T15:00:00'},
            {'date': datetime(2013, 5, 15, 15, 0, 0)}
        ),
        (
            {'foo': {'date': '2013-05-15T15:00:00'}},
            {'foo': {'date': datetime(2013, 5, 15, 15, 0, 0)}}
        ),
        (
            {'foo': ['2013-05-15T15:00:00', '2013-03-03T03:00:00']},
            {'foo': [datetime(2013, 5, 15, 15, 0, 0),
                     datetime(2013, 3, 3, 3, 0, 0)]}
        ),
        (
            {'date': '2013-05-15ou8120:00'},
            {'date': '2013-05-15ou8120:00'},
        ),
        (
            {'date': u'\x00013-05-15T15:00:00'},
            {'date': u'\x00013-05-15T15:00:00'},
        ),
    ]

    for obj, expected in tests:
        yield check_to_python, obj, expected
