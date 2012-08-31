from unittest import TestCase

from nose.tools import eq_

from elasticutils import get_es, DEFAULT_TIMEOUT, DEFAULT_INDEXES


class ESTest(TestCase):
    def test_get_es_defaults(self):
        """Test that the ES has the correct defaults."""
        es = get_es()
        eq_(es.timeout, DEFAULT_TIMEOUT)
        # dump_curl defaults to False, but if dump_curl is Falsey,
        # then pyes.es.ES sets its dump_curl attribute to None.
        eq_(es.dump_curl, None)
        eq_(es.default_indexes, DEFAULT_INDEXES)

    def test_get_es_overriding_defaults(self):
        """Test that overriding defaults works."""
        class Dumper(object):
            def write(self, val):
                print val

        d = Dumper()

        es = get_es(timeout=20, dump_curl=d,
                    default_indexes=['joe'])

        eq_(es.timeout, 20)
        eq_(es.dump_curl, d)
        eq_(es.default_indexes, ['joe'])


