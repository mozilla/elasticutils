from nose.tools import eq_

from elasticutils.tests import ESTestCase


class MonkeyPatchTest(ESTestCase):
    mapping_type_name = 'eutestcolor'
        
    def test_bulk_insert_update_delete(self):
        es = self.get_es()

        # Bulk index two things and then verify they made it into the
        # index.
        data = [
            {'index': {'_index': self.index_name,
                       '_type': self.mapping_type_name,
                       '_id': 1}},
            {'color': 'blue'},

            {'index': {'_index': self.index_name,
                       '_type': self.mapping_type_name,
                       '_id': 2}},
            {'color': 'red'},
        ]
        es.bulk(data, refresh=True)

        eq_(len(self.get_s()), 2)
        eq_(self.get_s().filter(color='blue')[0]._id, '1')
        eq_(self.get_s().filter(color='red')[0]._id, '2')

        # Then bulk update them.
        data = [
            {'update': {'_index': self.index_name,
                        '_type': self.mapping_type_name,
                        '_id': 1}},
            {'doc': {'color': 'green'}},

            {'update': {'_index': self.index_name,
                        '_type': self.mapping_type_name,
                        '_id': 2}},
            {'doc': {'color': 'pink'}}
        ]
        es.bulk(data, refresh=True)
            
        eq_(len(self.get_s()), 2)
        eq_(len(self.get_s().filter(color='blue')), 0)
        eq_(len(self.get_s().filter(color='red')), 0)

        eq_(self.get_s().filter(color='green')[0]._id, '1')
        eq_(self.get_s().filter(color='pink')[0]._id, '2')

        # Then delete them and make sure they're gone.
        data = [
            {'delete': {'_index': self.index_name,
                        '_type': self.mapping_type_name,
                        '_id': 1}},
            {'delete': {'_index': self.index_name,
                        '_type': self.mapping_type_name,
                        '_id': 2}}
        ]
        es.bulk(data, refresh=True)

        eq_(len(self.get_s()), 0)

    def test_bulk_create(self):
        es = self.get_es()

        # Bulk create two things and then verify they made it into the
        # index.
        data = [
            {'create': {'_index': self.index_name,
                       '_type': self.mapping_type_name,
                       '_id': 1}},
            {'color': 'blue'},

            {'create': {'_index': self.index_name,
                       '_type': self.mapping_type_name,
                       '_id': 2}},
            {'color': 'red'},
        ]
        es.bulk(data, refresh=True)

        eq_(len(self.get_s()), 2)
        eq_(self.get_s().filter(color='blue')[0]._id, '1')
        eq_(self.get_s().filter(color='red')[0]._id, '2')
