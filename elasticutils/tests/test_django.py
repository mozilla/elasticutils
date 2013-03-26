from functools import wraps
from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_

from elasticutils.tests import ElasticTestCase, facet_counts_dict


# TODO: To run this file or import it requires Django be installed.
# If Django isn't installed, we want to skip each test individually.
# However, those requirements create a lot of tangled stuff in here.
# It'd be nice if we could do this in a less tangled way and also skip
# the tests individually (so it's easy to see which tests got skipped
# and why) if Django isn't installed.


SKIP_TESTS = False


try:
    from django.conf import settings
    from django.test import RequestFactory
    from django.test.utils import override_settings

    from elasticutils.contrib.django import (
        S, F, get_es, InvalidFieldActionError, ES_EXCEPTIONS,
        ESExceptionMiddleware, es_required_or_50x)
    from elasticutils.contrib.django.tasks import (
        index_objects, unindex_objects)
    from elasticutils.tests.django_utils import (
        FakeDjangoMappingType, FakeModel, reset_model_cache)
except ImportError:
    SKIP_TESTS = True

    def override_settings(*args, **kw):
        def wrapper(func):
            return func
        return wrapper


def require_django_or_skip(fun):
    @wraps(fun)
    def _require_django_or_skip(*args, **kwargs):
        if SKIP_TESTS:
            raise SkipTest
        return fun(*args, **kwargs)
    return _require_django_or_skip


class DjangoElasticTestCase(ElasticTestCase):
    @classmethod
    def setup_class(cls):
        if cls.skip_tests or SKIP_TESTS:
            return

        super(DjangoElasticTestCase, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        if cls.skip_tests or SKIP_TESTS:
            return

        super(DjangoElasticTestCase, cls).setup_class()


class TestS(TestCase):
    @require_django_or_skip
    def test_require_mapping_type(self):
        """The Django S requires a mapping type."""
        self.assertRaises(TypeError, S)

    @require_django_or_skip
    def test_get_indexes(self):
        """Test get_indexes always returns a list of strings."""

        # Pulls it from ES_INDEXES (list of strings).
        s = S(FakeDjangoMappingType)
        eq_(s.get_indexes(), ['elasticutilstest'])

        # Pulls it from ES_INDEXES (string).
        old_indexes = settings.ES_INDEXES
        try:
            settings.ES_INDEXES = {'default': 'elasticutilstest'}

            s = S(FakeDjangoMappingType)
            eq_(s.get_indexes(), ['elasticutilstest'])
        finally:
            settings.ES_INDEXES = old_indexes

        # Pulls from indexes.
        s = S(FakeDjangoMappingType).indexes('footest')
        eq_(s.get_indexes(), ['footest'])

        s = S(FakeDjangoMappingType).indexes('footest', 'footest2')
        eq_(s.get_indexes(), ['footest', 'footest2'])

        s = S(FakeDjangoMappingType).indexes('footest').indexes('footest2')
        eq_(s.get_indexes(), ['footest2'])

    @require_django_or_skip
    def test_get_doctypes(self):
        """Test get_doctypes always returns a list of strings."""
        # Pulls from ._meta.db_table.
        s = S(FakeDjangoMappingType)
        eq_(s.get_doctypes(), ['fake'])

        # Pulls from doctypes.
        s = S(FakeDjangoMappingType).doctypes('footype')
        eq_(s.get_doctypes(), ['footype'])

        s = S(FakeDjangoMappingType).doctypes('footype', 'footype2')
        eq_(s.get_doctypes(), ['footype', 'footype2'])

        s = S(FakeDjangoMappingType).doctypes('footype').doctypes('footype2')
        eq_(s.get_doctypes(), ['footype2'])


class QueryTest(DjangoElasticTestCase):
    @classmethod
    def setup_class(cls):
        if cls.skip_tests or SKIP_TESTS:
            return

        super(QueryTest, cls).setup_class()

        cls.create_index()

        data = [
            {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
            {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
            {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
            {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
            {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
            ]
        cls.index_data(data,
                       index=FakeDjangoMappingType.get_index(),
                       doctype=FakeDjangoMappingType.get_mapping_type_name())

        # Generate all the FakeModels in our "database"
        for args in data:
            FakeModel(**args)

        cls.refresh()

    @require_django_or_skip
    def test_q(self):
        eq_(len(S(FakeDjangoMappingType).query(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).query(foo='car')), 2)

    @require_django_or_skip
    def test_q_all(self):
        eq_(len(S(FakeDjangoMappingType)), 5)

    @require_django_or_skip
    def test_filter_empty_f(self):
        eq_(len(S(FakeDjangoMappingType).filter(F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() | F() | F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F() & F() & F(tag='awesome'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F())), 5)

    @require_django_or_skip
    def test_filter(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome')), 3)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome'))), 3)

    @require_django_or_skip
    def test_filter_and(self):
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome', foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(tag='awesome').filter(foo='bar')), 1)
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') & F(foo='bar'))), 1)

    @require_django_or_skip
    def test_filter_or(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat'))), 4)

    @require_django_or_skip
    def test_filter_or_3(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome') | F(tag='boat') |
                                     F(tag='boring'))), 5)
        eq_(len(S(FakeDjangoMappingType).filter(or_={'foo': 'bar',
                                          'or_': {'tag': 'boat',
                                                  'width': '5'}
                                          })), 3)

    @require_django_or_skip
    def test_filter_complicated(self):
        eq_(len(S(FakeDjangoMappingType).filter(F(tag='awesome', foo='bar') |
                                     F(tag='boring'))), 2)

    @require_django_or_skip
    def test_filter_not(self):
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='awesome'))), 2)
        eq_(len(S(FakeDjangoMappingType).filter(~(F(tag='boring') | F(tag='boat')))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat')).filter(~F(foo='bar'))), 3)
        eq_(len(S(FakeDjangoMappingType).filter(~F(tag='boat', foo='barf'))), 5)

    @require_django_or_skip
    def test_filter_bad_field_action(self):
        with self.assertRaises(InvalidFieldActionError):
            len(S(FakeDjangoMappingType).filter(F(tag__faux='awesome')))

    @require_django_or_skip
    def test_facet(self):
        qs = S(FakeDjangoMappingType).facet('tag')
        eq_(facet_counts_dict(qs, 'tag'), dict(awesome=3, boring=1, boat=1))

    @require_django_or_skip
    def test_filtered_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # filter doesn't apply to facets
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # filter does apply to facets
        eq_(facet_counts_dict(qs.facet('tag', filtered=True), 'tag'),
            {'awesome': 1})

    @require_django_or_skip
    def test_global_facet(self):
        qs = S(FakeDjangoMappingType).query(foo='car').filter(width=5)

        # facet restricted to query
        eq_(facet_counts_dict(qs.facet('tag'), 'tag'),
            {'awesome': 2})

        # facet applies to all of corpus
        eq_(facet_counts_dict(qs.facet('tag', global_=True), 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @require_django_or_skip
    def test_facet_raw(self):
        qs = S(FakeDjangoMappingType).facet_raw(tags={'terms': {'field': 'tag'}})
        eq_(facet_counts_dict(qs, 'tags'),
            dict(awesome=3, boring=1, boat=1))

        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet_raw(tags={'terms': {'field': 'tag'}}))
        eq_(facet_counts_dict(qs, 'tags'),
            {'awesome': 2})

    @require_django_or_skip
    def test_facet_raw_overrides_facet(self):
        """facet_raw overrides facet with the same facet name."""
        qs = (S(FakeDjangoMappingType)
              .query(foo='car')
              .facet('tag')
              .facet_raw(tag={'terms': {'field': 'tag'}, 'global': True}))
        eq_(facet_counts_dict(qs, 'tag'),
            dict(awesome=3, boring=1, boat=1))

    @require_django_or_skip
    def test_order_by(self):
        res = S(FakeDjangoMappingType).filter(tag='awesome').order_by('-width')
        eq_([d.id for d in res], [5, 3, 1])


class IndexableTest(DjangoElasticTestCase):
    index_name = 'elasticutilstest'

    @classmethod
    def get_es(cls):
        return get_es()

    def setUp(self):
        super(IndexableTest, self).setUp()
        if self.skip_tests or SKIP_TESTS:
            return
        IndexableTest.create_index()

    def tearDown(self):
        super(IndexableTest, self).tearDown()
        if self.skip_tests or SKIP_TESTS:
            return
        IndexableTest.cleanup_index()

    @require_django_or_skip
    def test_refresh(self):
        FakeDjangoMappingType.refresh_index()

    @require_django_or_skip
    def test_index(self):
        document = {'id': 1, 'name': 'odin skullcrusher'}

        # Generate the FakeModel in our "database"
        FakeModel(**document)

        # Index the document with .index()
        FakeDjangoMappingType.index(document, id_=document['id'])

        IndexableTest.refresh()

        # Query it to make sure it's there.
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='odin')), 1)

    @require_django_or_skip
    def test_bulk_index(self):
        documents = [
            {'id': 1, 'name': 'odin skullcrusher'},
            {'id': 2, 'name': 'heimdall kneebiter'},
            {'id': 3, 'name': 'erik rose'}
            ]

        # Generate the FakeModel in our "database"
        for doc in documents:
            FakeModel(**doc)

        # Index the document with .index()
        FakeDjangoMappingType.bulk_index(documents, id_field='id')

        IndexableTest.refresh()

        # Query it to make sure they're there.
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='odin')), 1)
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='erik')), 1)


def require_celery_or_skip(fun):
    @wraps(fun)
    def _require_celery_or_skip(*args, **kwargs):
        try:
            import celery
        except ImportError:
            raise SkipTest
        return fun(*args, **kwargs)
    return _require_celery_or_skip


class TestTasks(DjangoElasticTestCase):
    index_name = 'elasticutilstest'

    @classmethod
    def get_es(cls):
        return get_es()

    def setUp(self):
        super(TestTasks, self).setUp()
        if self.skip_tests or SKIP_TESTS:
            return
        TestTasks.create_index()
        reset_model_cache()

    def tearDown(self):
        super(TestTasks, self).tearDown()
        if self.skip_tests or SKIP_TESTS:
            return
        TestTasks.cleanup_index()

    @require_celery_or_skip
    def test_tasks(self):
        documents = [
            {'id': 1, 'name': 'odin skullcrusher'},
            {'id': 2, 'name': 'heimdall kneebiter'},
            {'id': 3, 'name': 'erik rose'}
            ]

        for doc in documents:
            FakeModel(**doc)

        # Test index_objects task
        index_objects(FakeDjangoMappingType, [1, 2, 3])
        FakeDjangoMappingType.refresh_index()
        eq_(FakeDjangoMappingType.search().count(), 3)

        # Test unindex_objects task
        unindex_objects(FakeDjangoMappingType, [1, 2, 3])
        FakeDjangoMappingType.refresh_index()
        eq_(FakeDjangoMappingType.search().count(), 0)


class MiddlewareTest(DjangoElasticTestCase):

    def setUp(self):
        super(MiddlewareTest, self).setUp()
        if self.skip_tests or SKIP_TESTS:
            return

        def view(request, exc):
            raise exc

        self.func = view
        self.fake_request = RequestFactory().get('/')

    @require_django_or_skip
    def test_exceptions(self):
        for exc in ES_EXCEPTIONS:
            response = ESExceptionMiddleware().process_exception(
                self.fake_request, exc(Exception))
            eq_(response.status_code, 503)

    @require_django_or_skip
    @override_settings(ES_DISABLED=True)
    def test_es_disabled(self):
        response = ESExceptionMiddleware().process_request(self.fake_request)
        eq_(response.status_code, 501)


class DecoratorTest(DjangoElasticTestCase):

    def setUp(self):
        super(DecoratorTest, self).setUp()
        if self.skip_tests or SKIP_TESTS:
            return

        @es_required_or_50x()
        def view(request, exc):
            raise exc

        self.func = view
        self.fake_request = RequestFactory().get('/')

    @require_django_or_skip
    def test_exceptions(self):
        for exc in ES_EXCEPTIONS:
            response = self.func(self.fake_request, exc(Exception))
            eq_(response.status_code, 503)

    @require_django_or_skip
    @override_settings(ES_DISABLED=True)
    def test_es_disabled(self):
        response = self.func(self.fake_request)
        eq_(response.status_code, 501)
