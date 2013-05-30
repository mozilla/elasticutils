from unittest import TestCase

from nose.tools import eq_

from elasticutils import get_es, _cached_elasticsearch


class ESTest(TestCase):
    def setUp(self):
        super(ESTest, self).setUp()

        _cached_elasticsearch.clear()

    def test_get_es_caching(self):
        """Test get_es caching."""
        es = get_es()

        # Cached one item.
        eq_(len(_cached_elasticsearch), 1)

        # Use a different url, make sure that gets cached, too, and
        # it's different than the first one.
        es2 = get_es(urls=['http://example.com:9200'])
        eq_(len(_cached_elasticsearch), 2)
        assert id(es) != id(es2)

        # Use the same url, but pass it as a string, make sure that
        # pulls the previous one.
        es3 = get_es(urls='http://example.com:9200')
        eq_(len(_cached_elasticsearch), 2)
        assert id(es2) == id(es3)

        # Use a different timeout.
        es4 = get_es(timeout=10)
        eq_(len(_cached_elasticsearch), 3)
        assert id(es) != id(es4)

    def test_get_es_force_new(self):
        """Test that force_new works correctly."""
        es = get_es()

        es2 = get_es(force_new=True)

        # force_new prevents the new ElasticSearch instance from getting
        # cached, so we should only have one item in the cache.
        eq_(len(_cached_elasticsearch), 1)

        # However, the two ElasticSearch instances should be different.
        assert id(es) != id(es2)

    def test_get_es_settings_cache(self):
        """Tests **settings and cache."""
        es = get_es(max_retries=5, revival_delay=10)
        eq_(len(_cached_elasticsearch), 1)

        # Switching the order doesn't affect caching.
        es2 = get_es(revival_delay=10, max_retries=5)
        eq_(len(_cached_elasticsearch), 1)
        assert id(es) == id(es2)

        # Different values brings up a new item.
        es3 = get_es(max_retries=4, revival_delay=10)
        eq_(len(_cached_elasticsearch), 2)
        assert id(es) != id(es3)
