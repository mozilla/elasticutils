from datetime import date, datetime
import pickle

from nose.tools import eq_

from elasticutils import S, DefaultMappingType, NoModelError, MappingType
from elasticutils.tests import ESTestCase


model_cache = []


def reset_model_cache():
    del model_cache[0:]


class Meta(object):
    def __init__(self, db_table):
        self.db_table = db_table


class Manager(object):
    def filter(self, id__in=None):
        return [m for m in model_cache if m.id in id__in]


class FakeModel(object):
    _meta = Meta('fake')
    objects = Manager()

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])
        model_cache.append(self)

    @classmethod
    def get(cls, id):
        id = int(id)
        return [m for m in model_cache if m.id == id][0]


class FakeMappingType(MappingType):
    @classmethod
    def get_index(cls):
        return 'elasticutilstestfmt'

    @classmethod
    def get_mapping_type_name(cls):
        return 'elasticutilsdoctypefmt'

    def get_model(self):
        return FakeModel


class TestResultsWithData(ESTestCase):
    data = [
        {'id': 1, 'foo': 'bar', 'tag': 'awesome', 'width': '2'},
        {'id': 2, 'foo': 'bart', 'tag': 'boring', 'width': '7'},
        {'id': 3, 'foo': 'car', 'tag': 'awesome', 'width': '5'},
        {'id': 4, 'foo': 'duck', 'tag': 'boat', 'width': '11'},
        {'id': 5, 'foo': 'train car', 'tag': 'awesome', 'width': '7'}
    ]

    @classmethod
    def teardown_class(cls):
        super(TestResultsWithData, cls).teardown_class()
        reset_model_cache()

    def test_default_results_are_default_mapping_type(self):
        """With untyped S, return dicts."""
        # Note: get_s with no args should return an untyped S
        searcher = list(self.get_s().query(foo='bar'))
        assert isinstance(searcher[0], DefaultMappingType)

    def test_typed_s_returns_type(self):
        """With typed S, return objects of type."""
        searcher = list(self.get_s(FakeMappingType).query(foo='bar'))
        assert isinstance(searcher[0], FakeMappingType)

    def test_values_dict_no_fields(self):
        """With values_dict, return list of dicts."""
        searcher = list(self.get_s().query(foo='bar').values_dict())
        assert isinstance(searcher[0], dict)

    def test_values_dict_results(self):
        """With values_dict, return list of dicts."""
        searcher = list(self.get_s()
                        .query(foo='bar')
                        .values_dict('foo', 'width'))
        assert isinstance(searcher[0], dict)
        eq_(
            sorted(searcher[0].items()),
            sorted([(u'foo', [u'bar']), (u'width', [u'2'])])
        )

    def test_values_list_no_fields(self):
        """Specifying no fields with values_list returns what's stored."""
        searcher = list(self.get_s()
                        .query(foo='bar')
                        .values_list())
        assert isinstance(searcher[0], tuple)
        # We sort the result and expected result here so that the
        # order is stable and comparable.
        eq_(
            sorted(searcher[0]),
            sorted([[u'1'], [u'elasticutilsmappingtype']])
        )

    def test_values_list_results(self):
        """With values_list fields, returns list of tuples."""
        searcher = list(self.get_s()
                        .query(foo='bar')
                        .values_list('foo', 'width'))
        assert isinstance(searcher[0], tuple)
        eq_(
            sorted(searcher[0]),
            sorted(([u'2'], [u'bar']))
        )

    def test_default_results_form_has_metadata(self):
        """Test default results form has metadata."""
        searcher = list(self.get_s().query(foo='bar'))
        assert hasattr(searcher[0], '_id')
        assert hasattr(searcher[0].es_meta, 'id')
        assert hasattr(searcher[0].es_meta, 'score')
        assert hasattr(searcher[0].es_meta, 'source')
        assert hasattr(searcher[0].es_meta, 'type')
        assert hasattr(searcher[0].es_meta, 'explanation')
        assert hasattr(searcher[0].es_meta, 'highlight')

    def test_values_list_form_has_metadata(self):
        """Test default results form has metadata."""
        searcher = list(self.get_s().query(foo='bar').values_list('id'))
        assert hasattr(searcher[0], '_id')
        assert hasattr(searcher[0].es_meta, 'id')
        assert hasattr(searcher[0].es_meta, 'score')
        assert hasattr(searcher[0].es_meta, 'source')
        assert hasattr(searcher[0].es_meta, 'type')
        assert hasattr(searcher[0].es_meta, 'explanation')
        assert hasattr(searcher[0].es_meta, 'highlight')

    def test_values_dict_form_has_metadata(self):
        """Test default results form has metadata."""
        searcher = list(self.get_s().query(foo='bar').values_dict())
        assert hasattr(searcher[0], '_id')
        assert hasattr(searcher[0].es_meta, 'id')
        assert hasattr(searcher[0].es_meta, 'score')
        assert hasattr(searcher[0].es_meta, 'source')
        assert hasattr(searcher[0].es_meta, 'type')
        assert hasattr(searcher[0].es_meta, 'explanation')
        assert hasattr(searcher[0].es_meta, 'highlight')

    def test_values_dict_no_args(self):
        """Calling values_dict() with no args fetches all fields."""
        eq_(S().query(fld1=2)
               .values_dict()
               .build_search(),
            {"query": {"term": {"fld1": 2}}, 'fields': ['*']})

    def test_values_list_no_args(self):
        """Calling values_list() with no args fetches all fields."""
        eq_(S().query(fld1=2)
               .values_list()
               .build_search(),
            {'query': {"term": {"fld1": 2}}, 'fields': ['*']})


class TestResultsWithStoredFields(ESTestCase):
    def test_values_list_no_args_no_stored_fields(self):
        # If there are no fields specified in the values_list() call
        # and no stored fields for that document, then we pass in
        # fields=['*'] and ES returns nothing, so we return the _id
        # and _type.
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'weight': {'type': 'integer'},
                    }
                }
            }
        )
        data = [
            {'id': 1, 'name': 'bob', 'weight': 40}
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_list())
        eq_(sorted(results[0], key=repr),
            # Note: This is the _id of the document--not the "id" in
            # the document.
            sorted(([u'1'], [u'elasticutilsmappingtype']), key=repr)
        )

    def test_values_list_no_args_with_stored_fields(self):
        # If there are no fields specified, then ES returns the fields
        # marked as stored.
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer', 'store': True},
                        'name': {'type': 'string', 'store': True},
                        'weight': {'type': 'integer'},
                    }
                }
            }
        )

        data = [
            {'id': 1, 'name': 'bob', 'weight': 40}
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_list())
        eq_(sorted(results[0], key=repr),
            sorted(([1], [u'bob']), key=repr)
        )

    def test_values_dict_no_args_no_stored_fields(self):
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'weight': {'type': 'integer'},
                    }
                }
            }
        )
        data = [
            {'id': 1, 'name': 'bob', 'weight': 40}
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_dict())
        eq_(sorted(results[0].items()),
            # Note: This is the _id of the document--not the "id" in
            # the document.
            sorted([('_id', [u'1']), ('_type', [u'elasticutilsmappingtype'])])
        )

    def test_values_dict_no_args_with_stored_fields(self):
        # If there are no fields specified, then ES returns the fields
        # marked as stored.
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer', 'store': True},
                        'name': {'type': 'string', 'store': True},
                        'weight': {'type': 'integer'},
                    }
                }
            }
        )

        data = [
            {'id': 1, 'name': 'bob', 'weight': 40}
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_dict())
        eq_(sorted(results[0].items()),
            sorted([(u'id', [1]), (u'name', [u'bob'])])
        )


class TestFakeMappingType(ESTestCase):
    index_name = FakeMappingType.get_index()
    mapping_type_name = FakeMappingType.get_mapping_type_name()
    data = [
        {'id': 1, 'name': 'odin skullcrusher'},
        {'id': 2, 'name': 'olaf bloodbiter'}
    ]

    @classmethod
    def setup_class(cls):
        super(TestFakeMappingType, cls).setup_class()
        for doc in cls.data:
            FakeModel(**doc)

    @classmethod
    def teardown_class(cls):
        super(TestFakeMappingType, cls).setup_class()
        reset_model_cache()

    def test_object(self):
        s = S(FakeMappingType).query(name__prefix='odin')
        eq_(len(s), 1)
        eq_(s[0].object.id, 1)


class TestResultsWithDates(ESTestCase):
    def test_dates(self):
        """Datetime strings in ES results get converted to Python datetimes"""
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer'},
                        'bday': {'type': 'date', 'format': 'YYYY-mm-dd'},
                        'btime': {'type': 'date'}
                    }
                }
            }
        )
        data = [
            {'id': 1, 'bday': date(2012, 12, 1),
             'btime': datetime(2012, 12, 1, 12, 00)},
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_dict('id', 'bday', 'btime'))
        eq_(results,
            [{u'bday': [datetime(2012, 12, 1, 0, 0)],
              u'btime': [datetime(2012, 12, 1, 12, 0)],
              u'id': [1]}]
        )

    def test_dates_lookalikes(self):
        """Datetime strings in ES results get converted to Python datetimes"""
        self.cleanup_index()
        self.create_index(
            mappings={
                self.mapping_type_name: {
                    'properties': {
                        'id': {'type': 'integer'},
                        'bday': {'type': 'string', 'analyzer': 'keyword'}
                    }
                }
            }
        )
        data = [
            {'id': [1], 'bday': ['xxxx-xx-xxTxx:xx:xx']}
        ]

        self.index_data(data)
        self.refresh()

        results = list(self.get_s().values_dict('id', 'bday'))
        eq_(results,
            [{u'id': [1], u'bday': [u'xxxx-xx-xxTxx:xx:xx']}]
        )


class TestMappingType(ESTestCase):
    def setUp(self):
        super(TestMappingType, self).setUp()
        self.cleanup_index()
        self.create_index()

    def tearDown(self):
        self.cleanup_index()
        super(TestMappingType, self).tearDown()

    def test_default_mapping_type(self):
        data = [
            {'id': 1, 'name': 'Alice'}
        ]

        self.index_data(data)
        s = self.get_s(DefaultMappingType)
        result = list(s)[0]

        assert isinstance(result, DefaultMappingType)
        eq_(result.id, 1)
        self.assertRaises(NoModelError, lambda: result.object)

    def test_mapping_type_attribute_override(self):
        data = [
            {'id': 1, '_object': 'foo'}
        ]

        self.index_data(data)
        s = self.get_s(DefaultMappingType)
        result = list(s)[0]

        # Instance attribute (which starts out as None) takes precedence.
        eq_(result._object, None)
        # _object ES result field is available through __getitem__
        eq_(result['_object'], 'foo')  # key/val from ES

        # Get the ES result field id
        eq_(result.id, 1)
        # Set id to something else
        result.id = 'foo'
        # Now it returns the instance attribute
        eq_(result.id, 'foo')
        # id still available through __getitem__
        eq_(result['id'], 1)

        # If it doesn't exist, throw AttributeError
        self.assertRaises(AttributeError, lambda: result.doesnt_exist)
        # If it doesn't exist, throw KeyError
        self.assertRaises(KeyError, lambda: result['doesnt_exist'])

    def test_pickleable(self):
        data = [
            {'id': 1, '_object': 'foo'}
        ]

        self.index_data(data)
        s = self.get_s(DefaultMappingType)
        result = list(s)[0]

        pickled_mt = pickle.dumps(result, 2)
        unpickled = pickle.loads(pickled_mt)
        eq_(unpickled.id, 1)
