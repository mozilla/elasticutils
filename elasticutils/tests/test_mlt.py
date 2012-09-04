from nose.tools import eq_

from elasticutils import MLT, S
from elasticutils.tests import FakeModel, ElasticTestCase, facet_counts_dict


class HasDataTestCase(ElasticTestCase):
    @classmethod
    def setup_class(cls):
        super(HasDataTestCase, cls).setup_class()
        if cls.skip_tests:
            return

        es = cls.get_es()
        es.delete_index_if_exists(cls.index_name)

        data = []
        data.append(FakeModel(id=1, foo='bar', tag='awesome'))
        data.append(FakeModel(id=2, foo='bar', tag='boring'))
        data.append(FakeModel(id=3, foo='bar', tag='awesome'))
        data.append(FakeModel(id=4, foo='bar', tag='boring'))
        data.append(FakeModel(id=5, foo='bar', tag='elite'))
        data.append(FakeModel(id=6, foo='notbar', tag='gross'))
        data.append(FakeModel(id=7, foo='notbar', tag='awesome'))

        for datum in data:
            es.index(datum.__dict__, cls.index_name, FakeModel._meta.db_table,
                    bulk=True, id=datum.id)
        es.refresh()

    @classmethod
    def teardown_class(cls):
        super(HasDataTestCase, cls).teardown_class()
        if cls.skip_tests:
            return

        es = cls.get_es()
        es.delete_index(cls.index_name)

    def get_s(self):
        return S().indexes(
            self.index_name).doctypes(FakeModel._meta.db_table).values_dict()


class MoreLikeThisTest(HasDataTestCase):
    def test_bad_mlt(self):
        """Tests S or index and doc_type is specified."""
        self.assertRaises(ValueError, lambda: MLT(1))
        self.assertRaises(ValueError, lambda: MLT(1, index='foo'))
        self.assertRaises(ValueError, lambda: MLT(1, doctype='foo'))

    def test_mlt_on_foo(self):
        """Verify MLT with the foo field."""
        # We need to pass min_term_freq and min_doc_freq, because the terms
        # we are using are only once in each document.
        mlt = MLT(1, self.get_s(), ['foo'], min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 4)

    def test_mlt_on_foo_no_s(self):
        """Verify MLT with the foo field."""
        index = self.get_s().get_indexes()[0]
        doc_type = self.get_s().get_doctypes()[0]
        es = self.get_s().get_es()

        mlt = MLT(1, fields=['foo'], index=index, doctype=doc_type,
                  es=es, min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 4)

    def test_mlt_on_tag(self):
        """Verify MLT with the tag field."""
        # We need to pass min_term_freq and min_doc_freq, because the terms
        # we are using are only once in each document.
        mlt = MLT(1, self.get_s(), ['tag'], min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 2)

    def test_mlt_on_two_fields(self):
        """Verify MLT on tag and foo fields."""
        mlt = MLT(1, self.get_s(), ['tag', 'foo'],
                  min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 5)

    def test_mlt_on_foo_with_filter(self):
        """Verify MLT with the foo field while filtering on tag."""
        # We need to pass min_term_freq and min_doc_freq, because the terms
        # we are using are only once in each document.
        mlt = MLT(1, self.get_s().filter(tag='boring'), ['foo'],
                  min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 2)

        mlt = MLT(1, self.get_s().filter(tag='elite'), ['foo'],
                  min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 1)

        mlt = MLT(1, self.get_s().filter(tag='awesome'), ['foo'],
                  min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 1)

        mlt = MLT(1, self.get_s().filter(tag='gross'), ['foo'],
                  min_term_freq=1, min_doc_freq=1)
        eq_(len(mlt), 0)
