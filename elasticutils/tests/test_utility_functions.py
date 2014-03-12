from unittest import TestCase

from nose.tools import eq_

from elasticutils import S
from elasticutils.utils import chunked, to_json


class Testto_json(TestCase):
    def test_to_json(self):
        eq_(to_json({'query': {'match': {'message': 'test message'}}}),
            '{"query": {"match": {"message": "test message"}}}')

        eq_(to_json(S().query(message__match='test message').build_search()),
            '{"query": {"match": {"message": "test message"}}}')


class Testchunked(TestCase):
    def test_chunked(self):
        # chunking nothing yields nothing.
        eq_(list(chunked([], 1)), [])

        # chunking list where len(list) < n
        eq_(list(chunked([1], 10)), [(1,)])

        # chunking a list where len(list) == n
        eq_(list(chunked([1, 2], 2)), [(1, 2)])

        # chunking list where len(list) > n
        eq_(list(chunked([1, 2, 3, 4, 5], 2)),
            [(1, 2), (3, 4), (5,)])
