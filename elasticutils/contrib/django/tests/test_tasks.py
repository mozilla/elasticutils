from nose.tools import eq_

from elasticutils.contrib.django import get_es
from elasticutils.contrib.django.tasks import index_objects, unindex_objects
from elasticutils.contrib.django.tests import (
    FakeDjangoMappingType, FakeModel, reset_model_cache)
from elasticutils.contrib.django.estestcase import ESTestCase


class TestTasks(ESTestCase):
    @classmethod
    def get_es(cls):
        return get_es()

    def setUp(self):
        super(TestTasks, self).setUp()
        TestTasks.create_index(FakeDjangoMappingType.get_index())
        reset_model_cache()

    def tearDown(self):
        super(TestTasks, self).tearDown()
        TestTasks.cleanup_index(FakeDjangoMappingType.get_index())

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

    def test_tasks_chunk_size(self):
        """Test chunk size affects bulk_index"""
        documents = [
            {'id': 1, 'name': 'odin skullcrusher'},
            {'id': 2, 'name': 'heimdall kneebiter'},
            {'id': 3, 'name': 'erik rose'}
        ]

        for doc in documents:
            FakeModel(**doc)

        class MockMappingType(FakeDjangoMappingType):
            bulk_index_count = 0

            @classmethod
            def bulk_index(cls, *args, **kwargs):
                cls.bulk_index_count += 1

        index_objects(MockMappingType, [1, 2, 3])
        eq_(MockMappingType.bulk_index_count, 1)

        MockMappingType.bulk_index_count = 0

        index_objects(MockMappingType, [1, 2, 3], chunk_size=2)
        eq_(MockMappingType.bulk_index_count, 2)

        MockMappingType.bulk_index_count = 0

        index_objects(MockMappingType, [1, 2, 3], chunk_size=1)
        eq_(MockMappingType.bulk_index_count, 3)
