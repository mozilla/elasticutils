from nose.tools import eq_

from elasticutils.contrib.django import S, get_es
from elasticutils.contrib.django.tests import (
    FakeDjangoMappingType, FakeModel, reset_model_cache)
from elasticutils.contrib.django.estestcase import ESTestCase


class IndexableTest(ESTestCase):
    @classmethod
    def get_es(cls):
        return get_es()

    def setUp(self):
        super(IndexableTest, self).setUp()
        IndexableTest.create_index(FakeDjangoMappingType.get_index())

    def tearDown(self):
        super(IndexableTest, self).tearDown()
        IndexableTest.cleanup_index(FakeDjangoMappingType.get_index())
        reset_model_cache()

    def persist_data(self, data):
        for doc in data:
            FakeModel(**doc)

            # Index the document with .index()
            FakeDjangoMappingType.index(doc, id_=doc['id'])

        self.refresh(FakeDjangoMappingType.get_index())

    def test_refresh(self):
        FakeDjangoMappingType.refresh_index()

    def test_index(self):
        self.persist_data([
                {'id': 1, 'name': 'odin skullcrusher'},
                {'id': 2, 'name': 'olaf bloodbiter'},
        ])

        # Query it to make sure it's there.
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='odin')), 1)

    def test_get_object(self):
        self.persist_data([
                {'id': 1, 'name': 'odin skullcrusher'},
                {'id': 2, 'name': 'olaf bloodbiter'},
        ])

        s = S(FakeDjangoMappingType).query(name__prefix='odin')
        obj = s[0]
        eq_(obj.object.id, 1)

    def test_get_indexable(self):
        self.persist_data([
                {'id': 1, 'name': 'odin skullcrusher'},
                {'id': 2, 'name': 'olaf bloodbiter'},
        ])

        eq_(list(FakeDjangoMappingType.get_indexable()), [1, 2])

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

        self.refresh(FakeDjangoMappingType.get_index())

        # Query it to make sure they're there.
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='odin')), 1)
        eq_(len(S(FakeDjangoMappingType).query(name__prefix='erik')), 1)
