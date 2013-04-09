from unittest import TestCase

from django.conf import settings
from nose.tools import eq_

from elasticutils.contrib.django import S
from elasticutils.contrib.django.tests import FakeDjangoMappingType


class TestS(TestCase):
    def test_require_mapping_type(self):
        """The Django S requires a mapping type."""
        self.assertRaises(TypeError, S)

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
