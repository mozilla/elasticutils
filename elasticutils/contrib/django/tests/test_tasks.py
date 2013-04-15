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
