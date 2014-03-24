from nose.tools import eq_

from elasticutils import get_es
from elasticutils import S, MappingType, Indexable
from elasticutils.tests import ESTestCase


class FakeModel(object):
    _cache = {}

    @classmethod
    def reset(cls):
        cls._cache = {}

    def __init__(self, **fields):
        self.__dict__.update(fields)
        self._cache[fields['id']] = self

    def get(self, id):
        return self._cache[id]

    @classmethod
    def get_objects(self):
        return self._cache.values()


class FakeMappingType(MappingType, Indexable):
    @classmethod
    def get_index(cls):
        return ESTestCase.index_name

    @classmethod
    def get_mapping_type_name(cls):
        return ESTestCase.mapping_type_name

    @classmethod
    def get_model(cls):
        return FakeModel

    @classmethod
    def get_es(cls):
        return get_es(**ESTestCase.es_settings)

    @classmethod
    def get_mapping(cls):
        return {
            'properties': {
                'id': {'type': 'integer'},
                'title': {'type': 'string'},
                'tags': {'type': 'string'}
            }
        }

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        if obj == None:
            obj = cls.get_model().get(id=obj_id)

        doc = {}
        doc['id'] = obj.id
        doc['title'] = obj.title
        doc['tags'] = obj.tags
        return doc

    @classmethod
    def get_indexable(cls):
        return cls.get_model().get_objects()


class ModelTest(ESTestCase):
    mapping_type_name = FakeMappingType.get_mapping_type_name()
    mapping = {
        FakeMappingType.get_mapping_type_name(): FakeMappingType.get_mapping()
    }

    def test_refresh(self):
        """Calling refresh_index shouldn't throw an exception"""
        FakeMappingType.refresh_index()

    def setUp(self):
        super(ESTestCase, self).setUp()
        ESTestCase.setup_class()

    def tearDown(self):
        super(ESTestCase, self).tearDown()
        ESTestCase.teardown_class()
        FakeModel.reset()

    def test_index(self):
        obj1 = FakeModel(id=1, title='First post!', tags=['blog', 'post'])
        FakeMappingType.index(
            FakeMappingType.extract_document(obj_id=obj1.id, obj=obj1),
            id_=obj1.id)

        FakeMappingType.refresh_index()

        s = S(FakeMappingType)
        eq_(s.count(), 1)
        eq_(list(s.execute())[0].title, obj1.title)

    def test_bulk_index(self):
        FakeModel(id=1, title='First post!', tags=['blog', 'post'])
        FakeModel(id=2, title='Second post!', tags=['blog', 'post'])

        documents = []
        for obj in FakeModel.get_objects():
            documents.append(
                FakeMappingType.extract_document(obj_id=obj.id, obj=obj))

        FakeMappingType.bulk_index(documents, id_field='id')
        FakeMappingType.refresh_index()
            
        s = S(FakeMappingType)
        eq_(s.count(), 2)
        eq_(sorted([res.title for res in s.execute()]),
            ['First post!', 'Second post!'])

    def test_unindex(self):
        obj1 = FakeModel(id=1, title='First post!', tags=['blog', 'post'])
        FakeMappingType.index(
            FakeMappingType.extract_document(obj_id=obj1.id, obj=obj1),
            id_=obj1.id)

        FakeMappingType.refresh_index()

        s = S(FakeMappingType)
        eq_(s.count(), 1)
        eq_(list(s.execute())[0].title, obj1.title)

        FakeMappingType.unindex(id_=obj1.id)
        FakeMappingType.refresh_index()

        s = S(FakeMappingType)
        eq_(s.count(), 0)
