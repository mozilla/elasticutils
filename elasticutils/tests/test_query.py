from datetime import datetime, timedelta
from unittest import TestCase

from nose.tools import eq_

from elasticutils import (
    S, F, Q, BadSearch, InvalidFieldActionError, InvalidFacetType,
    InvalidFlagsError, SearchResults, DefaultMappingType, MappingType,
    DEFAULT_INDEXES, DEFAULT_DOCTYPES)
from elasticutils.tests import ESTestCase, facet_counts_dict, require_version
import six


def eqish_(item1, item2):
    """Compare two trees ignoring order of things in lists

    Note: This is really goofy, but works for our specific purposes. If you
    have other needs, you'll likely need to find a new solution here.

    """
    def _eqish(part1, part2):
        if type(part1) != type(part2) or bool(part1) != bool(part2):
            return False

        if isinstance(part1, (tuple, list)):
            # This is kind of awful, but what we need to do is make
            # sure everything in the list part1 is in the list part2
            # in an eqish way.
            part2_left = list(part2)

            for mem1 in part1:
                for i, mem2 in enumerate(part2_left):
                    if _eqish(mem1, mem2):
                        del part2_left[i]
                        break
                else:
                    return False
            return True

        elif isinstance(part1, dict):
            if sorted(part1.keys()) != sorted(part2.keys()):
                return False
            for mem in part1.keys():
                if not _eqish(part1[mem], part2[mem]):
                    return False
            return True

        else:
            return part1 == part2

    if not _eqish(item1, item2):
        raise AssertionError('{0} != {1}'.format(item1, item2))


class TestEqish(TestCase):
    def test_good(self):
        eqish_('a', 'a')
        eqish_(True, True)
        eqish_(1, 1)
        eqish_([1, 2, 3], [1, 2, 3])
        eqish_([1, 2, 3], [3, 2, 1])
        eqish_({'a': [1, 2, 3]},
               {'a': [3, 2, 1]})
        eqish_({'a': {'b': [1, 2, 3]}},
               {'a': {'b': [3, 2, 1]}})
        eqish_(
            {
                'filter': {
                    'or': [
                        {'term': {'foo': 'bar'}},
                        {'or': [
                            {'term': {'tag': 'boat'}},
                            {'term': {'width': '5'}}
                        ]}
                    ]}
            },
            {
                'filter': {
                    'or': [
                        {'or': [
                            {'term': {'width': '5'}},
                            {'term': {'tag': 'boat'}}
                        ]},
                        {'term': {'foo': 'bar'}}
                    ]}
            }
        )


    def test_bad(self):
        self.assertRaises(AssertionError,
                          lambda: eqish_({'a': [1, 2, 3]}, {'b': [1, 2, 3]}))
        self.assertRaises(AssertionError,
                          lambda: eqish_({'a': [1, 2, 3]}, {'a': [2, 3, 4]}))


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
        q = Q(foo__match='abc', bar__match='def', should=True)
        eq_(sorted(q.should_q), [('bar__match', 'def'), ('foo__match', 'abc')])
        eq_(sorted(q.must_q), [])
        eq_(sorted(q.must_not_q), [])

    def test_q_must(self):
        q = Q(foo__match='abc', bar__match='def', must=True)
        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [('bar__match', 'def'), ('foo__match', 'abc')])
        eq_(sorted(q.must_not_q), [])

    def test_q_must_not(self):
        q = Q(foo__match='abc', bar__match='def', must_not=True)
        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [])
        eq_(sorted(q.must_not_q), [('bar__match', 'def'), ('foo__match', 'abc')])

    def test_q_must_should(self):
        with self.assertRaises(InvalidFlagsError):
            Q(foo__match='abc', must=True, should=True)

    def test_q_basic_add(self):
        """Adding one Q to another Q combines them."""
        q = Q(foo__match='abc') + Q(bar__match='def')

        eq_(sorted(q.should_q), [])
        eq_(sorted(q.must_q), [('bar__match', 'def'), ('foo__match', 'abc')])
        eq_(sorted(q.must_not_q), [])

    def test_q_order(self):
        q1 = Q(foo__match='abc') + Q(bar__match='def')

        q2 = Q(bar__match='def') + Q(foo__match='abc')
        eq_(q1, q2)

        q2 = Q(bar__match='def')
        q2 += Q(foo__match='abc')
        eq_(q1, q2)

        q2 = Q(foo__match='abc')
        q2 += Q(bar__match='def')
        eq_(q1, q2)

    def test_q_mixed(self):
        q1 = Q(foo__match='should', bar__match='should', should=True)
        q2 = Q(baz='must')
        q3 = Q(bat='must_not', must_not=True)
        q4 = Q(ban='must', must=True)
        q5 = Q(bam='must', must=True)

        q_all = q1 + q2 + q3 + q4 + q5

        eq_(sorted(q_all.should_q),
            [('bar__match', 'should'), ('foo__match', 'should')])

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

    def test_q_match(self):
        eq_(len(self.get_s().query(foo__match='car')), 2)

        eq_(len(self.get_s().query(Q(foo__match='car'))), 2)

    def test_q_prefix(self):
        eq_(len(self.get_s().query(foo__prefix='ca')), 2)

        eq_(len(self.get_s().query(Q(foo__prefix='ca'))), 2)

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
        # Mispelled word gets no results with match query.
        eq_(len(self.get_s().query(foo__match='tran')), 0)

        eq_(len(self.get_s().query(Q(foo__match='tran'))), 0)

        # Mispelled word gets one result with fuzzy query.
        eq_(len(self.get_s().query(foo__fuzzy='tran')), 1)

        eq_(len(self.get_s().query(Q(foo__fuzzy='tran'))), 1)

    def test_q_wildcard(self):
        eq_(len(self.get_s().query(foo__wildcard='tra*n')), 1)
        eq_(len(self.get_s().query(foo__wildcard='tra?n')), 1)

        eq_(len(self.get_s().query(Q(foo__wildcard='tra*n'))), 1)
        eq_(len(self.get_s().query(Q(foo__wildcard='tra?n'))), 1)

    def test_q_demote(self):
        s = self.get_s().query(foo__match='car')
        scores = [(sr['id'], sr.es_meta.score) for sr in s.values_dict('id')]

        s = s.demote(0.5, width__term='5')
        demoted_scores = [(sr['id'], sr.es_meta.score) for sr in s.values_dict('id')]

        # These are both sorted by scores. We're demoting one result
        # so the top result in each list is different.
        assert scores[0] != demoted_scores

        # Now we do the whole thing again with Qs.
        s = self.get_s().query(Q(foo__match='car'))
        scores = [(sr['id'], sr.es_meta.score) for sr in s.values_dict('id')]

        s = s.demote(0.5, Q(width__term='5'))
        demoted_scores = [(sr['id'], sr.es_meta.score) for sr in s.values_dict('id')]

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
        eqish_(s.build_search(),
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
        eq_(s.build_search(),
            {'query': {'match': {'title': 'example'}}})

    def test_query_raw_overrides_everything(self):
        s = self.get_s().query_raw({'match': {'title': 'example'}})
        s = s.query(foo__match='foo')
        s = s.demote(0.5, title__match='bar')
        s = s.boost(title=5.0)

        eq_(s.build_search(),
            {'query': {'match': {'title': 'example'}}})

    def test_boost(self):
        """Boosted queries shouldn't raise a SearchPhaseExecutionException."""
        q1 = (self.get_s()
                  .boost(foo=4.0)
                  .query(foo='car', foo__match='car', foo__match_phrase='car'))

        # Make sure the query executes without throwing an exception.
        list(q1)

        # Verify it's producing the correct query.
        eqish_(q1.build_search(),
            {
                'query': {
                    'bool': {
                        'must': [
                            {'match_phrase': {'foo': {'query': 'car', 'boost': 4.0}}},
                            {'term': {'foo': {'value': 'car', 'boost': 4.0}}},
                            {'match': {'foo': {'query': 'car', 'boost': 4.0}}}
                        ]
                    }
                }
            })

        # Do the same thing with Qs.
        q1 = (self.get_s()
                  .boost(foo=4.0)
                  .query(Q(foo='car', foo__match='car', foo__match_phrase='car')))

        # Make sure the query executes without throwing an exception.
        list(q1)

        # Verify it's producing the correct query.
        eqish_(q1.build_search(),
            {
                'query': {
                    'bool': {
                        'must': [
                            {'match_phrase': {'foo': {'query': 'car', 'boost': 4.0}}},
                            {'term': {'foo': {'value': 'car', 'boost': 4.0}}},
                            {'match': {'foo': {'query': 'car', 'boost': 4.0}}}
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
            if six.PY3:
                out = dict([list(clause.items())[0]
                         for clause in search['query']['bool']['must']])
            else:
                out = dict([clause.items()[0]
                         for clause in search['query']['bool']['must']])
            return out

        q1 = self.get_s().boost(foo=4.0).query(foo='car', foo__prefix='car')
        eq_(_get_queries(q1.build_search())['term']['foo']['boost'], 4.0)
        eq_(_get_queries(q1.build_search())['prefix']['foo']['boost'], 4.0)

        q1 = q1.boost(foo=2.0)
        eq_(_get_queries(q1.build_search())['term']['foo']['boost'], 2.0)
        eq_(_get_queries(q1.build_search())['prefix']['foo']['boost'], 2.0)

        q1 = q1.boost(foo__prefix=4.0)
        eq_(_get_queries(q1.build_search())['term']['foo']['boost'], 2.0)
        eq_(_get_queries(q1.build_search())['prefix']['foo']['boost'], 4.0)

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
             .build_search()),
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
             .build_search()),
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
             .build_search()),
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
             .build_search()),
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
        eq_(s.build_search(),
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
            self.create_index(mappings=self.mapping)
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

    def test_count_empty_results(self):
        s = self.get_s()
        s.execute()

        # Simulate a situation where the result cache had 0 objects
        s._results_cache.objects = []
        s._results_cache.count = 123

        # Ensure that we are still retrieving the cached result count
        eq_(s.count(), 123)

    def test_len(self):
        assert isinstance(len(self.get_s()), int)

    def test_all(self):
        assert isinstance(self.get_s().all(), S)

    def test_everything(self):
        ret = self.get_s().everything()
        assert isinstance(ret, SearchResults)
        eq_(len(ret), len(self.data))

    def test_order_by(self):
        res = self.get_s().filter(tag='awesome').order_by('-width')
        eq_([d['id'] for d in res], [5, 3, 1])

    def test_order_by_dict(self):
        res = self.get_s().filter(tag='awesome').order_by({'width': 'desc'})
        eq_([d['id'] for d in res], [5, 3, 1])

    def test_slice(self):
        s = self.get_s().filter(tag='awesome')
        eq_(s.build_search(),
            {'filter': {'term': {'tag': 'awesome'}}})
        assert isinstance(s[0], DefaultMappingType)

        eq_(s[0:1].build_search(),
            {'filter': {'term': {'tag': 'awesome'}}, 'size': 1})

        eq_(s[1:2].build_search(),
            {'filter': {'term': {'tag': 'awesome'}}, 'from': 1, 'size': 1})

    def test_explain(self):
        qs = self.get_s().query(foo='car')

        assert 'explain' not in qs.build_search()

        qs = qs.explain(True)

        # You put the explain in...
        assert qs.build_search()['explain'] == True

        qs = qs.explain(False)

        # You take the explain out...
        assert 'explain' not in qs.build_search()

        # Shake it all about...
        qs = qs.explain(True)

        res = list(qs)
        assert res[0].es_meta.explanation


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
        eq_(s.build_search(), {})
        eq_(s.count(), 6)

    def test_filter_empty_f_or_f(self):
        s = self.get_s().filter(F() | F(tag='awesome'))
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_and_f(self):
        s = self.get_s().filter(F() & F(tag='awesome'))
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_f_and_empty_f(self):
        s = self.get_s().filter(F(tag='awesome') & F())
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_f_and_ff(self):
        s = self.get_s().filter(F(tag='awesome') & F(foo='car', width='7'))
        eqish_(s.build_search(),
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
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_and_empty_f_and_f(self):
        s = self.get_s().filter(F() & F() & F(tag='awesome'))
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_not_not_f(self):
        f = F(tag='awesome')
        f = ~f
        f = ~f
        s = self.get_s().filter(f)
        eq_(s.build_search(), {'filter': {'term': {'tag': 'awesome'}}})
        eq_(s.count(), 3)

    def test_filter_empty_f_not(self):
        s = self.get_s().filter(~F())
        eq_(s.build_search(), {})
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
        eqish_(s.build_search(), {
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
        eqish_(s.build_search(), {
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
        eq_(s.build_search(), {
                'filter': {
                    'not': {
                        'filter': {'term': {'tag': 'awesome'}}
                    }
                }
        })
        eq_(s.count(), 3)

        s = self.get_s().filter(~(F(tag='boring') | F(tag='boat')))
        eqish_(s.build_search(), {
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
        eqish_(s.build_search(), {
                'filter': {
                    'and': [
                        {'not': {'filter': {'term': {'tag': 'boat'}}}},
                        {'not': {'filter': {'term': {'foo': 'bar'}}}}
                    ]
                }
        })
        eq_(s.count(), 4)

        s = self.get_s().filter(~F(tag='boat', foo='barf'))
        eqish_(s.build_search(), {
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

    def test_filter_distance(self):
        s = self.get_s().filter(F(location__distance=('5km', 45, 10)))

        eqish_(s.build_search(), {
            'filter': {
                'geo_distance': {
                    'distance': '5km',
                    'location': [10, 45]
                }
            }
        })

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
        eq_(s.build_search(), {
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
        eq_(s.build_search(),
            {'filter': {'term': {'tag': 'awesome'}}})

    def test_filter_raw_overrides_everything(self):
        s = self.get_s().filter_raw({'term': {'tag': 'awesome'}})
        s = s.filter(tag='boring')
        s = s.filter(F(tag='end'))
        eq_(s.build_search(),
            {'filter': {'term': {'tag': 'awesome'}}})


class GeoFilterTest(ESTestCase):
    mapping = {
        ESTestCase.mapping_type_name: {
            'properties': {
                'id': {'type': 'integer'},
                'foo': {'type': 'string'},
                'tag': {'type': 'string'},
                'location': {'type': 'geo_point', 'store': True},
                'width': {'type': 'string', 'null_value': True}
                }
            }
        }

    data = [
        {'id': 1, 'location': [14.766654999999998, 40.9168853], 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
        {'id': 2, 'location': [14.7924042, 40.9275213], 'foo': 'bart', 'tag': 'boring', 'width': '7'},
        {'id': 3, 'location': [14.8167801, 40.9174042], 'foo': 'car', 'tag': 'awesome', 'width': '5'},
        {'id': 4, 'location': [14.6578217, 40.872507], 'foo': 'duck', 'tag': 'boat', 'width': '11'},
        {'id': 5, 'location': [14.9530792, 40.9804164], 'foo': 'car', 'tag': 'awesome', 'width': '7'},
        {'id': 6, 'location': [14.790612099999978, 40.914388], 'foo': 'caboose', 'tag': 'end', 'width': None}
    ]

    def test_filter_distance(self):
        coords = [14.790612099999978, 40.914388]

        s = self.get_s().filter(F(location__distance=('5km', coords[1], coords[0])))

        eqish_(s.build_search(), {
            'filter': {
                'geo_distance': {
                    'distance': '5km',
                    'location': [14.790612099999978, 40.914388]
                }
            }
        })

        eq_(len(s), 4)


class FacetTest(ESTestCase):
    def setUp(self):
        super(FacetTest, self).setUp()
        self.cleanup_index()
        self.create_index()

    def tearDown(self):
        super(FacetTest, self).tearDown()
        self.cleanup_index()

    def test_facet(self):
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

    def test_facet_with_size(self):
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome'},
                {'id': 2, 'foo': 'bart', 'tag': 'boring'},
                {'id': 3, 'foo': 'car', 'tag': 'awesome'},
                {'id': 4, 'foo': 'duck', 'tag': 'boat'},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome'},
                {'id': 6, 'foo': 'canoe', 'tag': 'boat'},
            ])
        FacetTest.refresh()

        qs = self.get_s()
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {u'boring': 1, u'awesome': 3, u'boat': 2})
        eq_(facet_counts_dict(qs.facet('tag', size=2), 'tag'),
            {u'awesome': 3, u'boat': 2})

    def test_filtered_facet(self):
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

    def test_filtered_facet_with_size(self):
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': 1},
                {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': 2},
                {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': 1},
                {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': 5},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': 5},
                {'id': 6, 'foo': 'canoe', 'tag': 'boat', 'width': 5},
                {'id': 7, 'foo': 'plane', 'tag': 'awesome', 'width': 5},
                {'id': 8, 'foo': 'cargo plane', 'tag': 'boring', 'width': 5},
            ])
        FacetTest.refresh()

        qs = self.get_s().filter(width=5)

        # regular facet
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'boring': 2, 'awesome': 4, 'boat': 2})
        # apply the filter
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'boring': 1, 'awesome': 2, 'boat': 2})
        # apply the filter and restrict the size
        eq_(facet_counts_dict(qs.facet('tag', size=2, filtered=True), 'tag'),
            {'awesome': 2, 'boat': 2})

    def test_filtered_facet_no_filters(self):
        FacetTest.index_data([
                {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': 1},
                {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': 2},
                {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': 1},
                {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': 5},
                {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': 5},
            ])
        FacetTest.refresh()

        qs = self.get_s().query(foo='car')

        # filtered=True doesn't cause a KeyError when there are no
        # filters
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 2})

    def test_global_facet(self):
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
        eq_(data["created1"].data,
            [
                {u'count': 3, u'term': u'red'},
                {u'count': 2, u'term': u'yellow'}
            ]
        )


    def test_facet_terms_other(self):
        """Test terms facet"""
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
        eq_(data["created1"].other, 4)

    def test_facet_terms_missing(self):
        """Test terms facet"""
        FacetTest.index_data([
                {'id': 1, 'color': 'red'},
                {'id': 2, 'color': 'red'},
                {'id': 3, 'color': 'red'},
                {'id': 4, 'color': 'yellow'},
                {'id': 5, 'colors': 'yellow'},
                {'id': 6, 'colors': 'green'},
                {'id': 7, 'colors': 'blue'},
                {'id': 8, 'colors': 'white'},
                {'id': 9, 'colors': 'brown'},
            ])
        FacetTest.refresh()

        qs = (self.get_s()
              .facet_raw(created1={
                    'terms': {
                        'field': 'color'
                    }
              })
        )

        data = qs.facet_counts()
        eq_(data["created1"].missing, 5)

    def test_facet_range(self):
        """Test range facet"""
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
              })
        )

        data = qs.facet_counts()
        eq_(data["created1"].data,
            [
                {u'count': 9, u'from': 0.0, u'min': 1.0, u'max': 4.0,
                 u'to': 5.0, u'total_count': 9, u'total': 20.0,
                 u'mean': 2.2222222222222223},
                {u'count': 0, u'from': 5.0, u'total_count': 0,
                 u'to': 20.0, u'total': 0.0, u'mean': 0.0}
            ]
        )

    def test_facet_histogram(self):
        """Test histogram facet"""
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
        eq_(data["created1"].data, [
                    {u'key': 0, u'count': 3},
                    {u'key': 2, u'count': 5},
                    {u'key': 4, u'count': 1},
                ])

    def test_facet_date_histogram(self):
        """facet_raw with date_histogram works."""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

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
        stat = data['created1']
        eq_(stat.count, 9)
        eq_(stat._type, u'statistical')
        eq_(stat.min, 1.0)
        eq_(stat.sum_of_squares, 54.0)
        eq_(stat.max, 4.0)
        eq_(stat.std_deviation, 1.0304020550550783)
        eq_(stat.variance, 1.0617283950617287)
        eq_(stat.total, 20.0)
        eq_(stat.mean, 2.2222222222222223)

    def test_filter_facet(self):
        """Test filter facet"""
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
        eq_(data['red_or_yellow']._type, 'filter')
        eq_(data['red_or_yellow'].count, 5)

    def test_query_facet(self):
        """Test query facet"""
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

        eq_(data['red_query']._type, 'query')
        eq_(data['red_query'].count, 3)

    def test_invalid_field_type(self):
        """Invalid _type should raise InvalidFacetType."""
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
    data = [
        {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
        {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
        {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
        {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
        {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
    ]

    def test_highlight_with_dict_results(self):
        """Make sure highlighting with dict-style results works.

        Highlighting should work on all fields specified in the ``highlight()``
        call, not just the ones mentioned in the query or in ``values_dict()``.

        """
        s = (self.get_s().query(foo__match='car')
                         .filter(id=5)
                         .highlight('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result.es_meta.highlight['foo'], [u'train <em>car</em>'])

        s = (self.get_s().query(foo__match='car')
                         .filter(id=5)
                         .highlight('tag', 'foo')
                         .values_dict('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result.es_meta.highlight['foo'], [u'train <em>car</em>'])

    def test_highlight_on_list_results(self):
        """Make sure highlighting with list-style results works.

        Highlighting should work on all fields specified in the ``highlight()``
        call, not just the ones mentioned in the query or in ``values_list()``.

        """
        s = (self.get_s().query(foo__match='car')
                         .filter(id=5)
                         .highlight('tag', 'foo')
                         .values_list('tag', 'foo'))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result.es_meta.highlight['foo'], [u'train <em>car</em>'])

    def test_highlight_options(self):
        """Make sure highlighting with options works."""
        s = (self.get_s().query(foo__match='car')
                         .filter(id=5)
                         .highlight('tag', 'foo',
                                    pre_tags=['<b>'],
                                    post_tags=['</b>']))
        result = list(s)[0]
        # The highlit text from the foo field should be in index 1 of the
        # excerpts.
        eq_(result.es_meta.highlight['foo'], [u'train <b>car</b>'])

    def test_highlight_cumulative(self):
        """Make sure highlighting fields are cumulative and none clears them."""
        # No highlighted fields means no highlights.
        s = (self.get_s().query(foo__match='car')
                         .filter(id=5)
                         .highlight())
        eq_(list(s)[0].es_meta.highlight, {})

        # Add a field and that gets highlighted.
        s = s.highlight('foo')
        eq_(list(s)[0].es_meta.highlight['foo'], [u'train <em>car</em>'])

        # Set it back to no fields and no highlight.
        s = s.highlight(None)
        eq_(list(s)[0].es_meta.highlight, {})


class SearchTypeTest(ESTestCase):
    # Set the mapping so shard allocation is controlled manually
    mapping = {
        ESTestCase.mapping_type_name: {
            'properties': {
                'id': {'type': 'integer'},
                'shard': {'type': 'integer'},
                'text': {'type': 'string'},
            },
            '_routing': {
                'required': True,
                'path': 'shard',
            },
        }
    }

    @classmethod
    def setup_class(cls):
        super(SearchTypeTest, cls).setup_class()
        cls.cleanup_index()

        # Explicitly create an index with 2 shards. The default
        # ES configuration is 5 shards, and should work as well,
        # but that could have been overridden (even though it is
        # a bad practice to create an index with one shard only).
        cls.create_index(settings={
            'number_of_shards': 2,
        })
        # These records will be allocated into different shards
        cls.index_data([
            {'id': 1, 'shard': 1, 'text': 'asdf'},
            {'id': 2, 'shard': 2, 'text': 'asdf'},
        ])
        cls.refresh()

    def test_query_and_fetch(self):
        s = self.get_s().search_type('query_and_fetch')

        # query_and_fetch combines results from every shard, therefore
        # limiting the query to 1 result will still produce two
        eq_(len(s[:1]), 2)


class ValuesTest(ESTestCase):
    def test_values_list_chaining(self):
        s = self.get_s()
        s = s.values_list()
        eqish_(s.build_search(),
               {
                   'fields': ['*']
               })

        s = s.values_list('id')
        eqish_(s.build_search(),
               {
                   'fields': ['id']
               })

        # Add new fields
        s = s.values_list('name', 'title')
        eqish_(s.build_search(),
               {
                   'fields': ['id', 'name', 'title']
               })

        # Fields don't show up more than once
        s = s.values_list('id')
        eqish_(s.build_search(),
               {
                   'fields': ['id', 'name', 'title']
               })

    def test_values_dict_chaining(self):
        s = self.get_s()
        s = s.values_dict()
        eqish_(s.build_search(),
               {
                   'fields': ['*']
               })

        s = s.values_dict('id')
        eqish_(s.build_search(),
               {
                   'fields': ['id']
               })

        # Add new fields
        s = s.values_dict('name', 'title')
        eqish_(s.build_search(),
               {
                   'fields': ['id', 'name', 'title']
               })

        # Fields don't show up more than once
        s = s.values_dict('id')
        eqish_(s.build_search(),
               {
                   'fields': ['id', 'name', 'title']
               })


class SuggestionTest(ESTestCase):
    data = [
        {'id': 1, 'name': 'bar'},
        {'id': 2, 'name': 'mark', 'location': 'mart'},
        {'id': 3, 'name': 'car'},
        {'id': 4, 'name': 'duck'},
        {'id': 5, 'name': 'train car'}
    ]

    @require_version('0.90')
    def test_suggestions(self):
        """Make sure correct suggestions are being returned.

        Test adding multiple ``suggest()`` clauses to the query, including
        different fields.

        """
        s = (self.get_s().query(name__match='mary')
                         .suggest('mysuggest', 'mary'))
        suggestions = s.suggestions()
        options = [o['text'] for o in suggestions['mysuggest'][0]['options']]
        eq_(options, ['mark', 'mart'])

        s = (self.get_s().query(name__match='mary')
                         .suggest('mysuggest', 'mary', field='name'))
        suggestions = s.suggestions()
        options = [o['text'] for o in suggestions['mysuggest'][0]['options']]
        eq_(options, ['mark'])


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
        (
            {'date': '2013-05-15T15:00:00.123456'},
            {'date': datetime(2013, 5, 15, 15, 0, 0, 123456)}
        ),
    ]

    for obj, expected in tests:
        yield check_to_python, obj, expected
