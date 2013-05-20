from nose.tools import eq_

from django.test import RequestFactory
from django.test.utils import override_settings

from elasticutils.contrib.django import (
    ES_EXCEPTIONS, ESExceptionMiddleware, es_required_or_50x)
from elasticutils.contrib.django.estestcase import ESTestCase


class MiddlewareTest(ESTestCase):
    def setUp(self):
        super(MiddlewareTest, self).setUp()

        def view(request, exc):
            raise exc

        self.func = view
        self.fake_request = RequestFactory().get('/')

    def test_exceptions(self):
        for exc in ES_EXCEPTIONS:
            response = ESExceptionMiddleware().process_exception(
                self.fake_request, exc(Exception))
            eq_(response.status_code, 503)
            self.assertTemplateUsed(response, 'elasticutils/503.html')

    @override_settings(ES_DISABLED=True)
    def test_es_disabled(self):
        response = ESExceptionMiddleware().process_request(self.fake_request)
        eq_(response.status_code, 501)
        self.assertTemplateUsed(response, 'elasticutils/501.html')


class DecoratorTest(ESTestCase):
    def setUp(self):
        super(DecoratorTest, self).setUp()

        @es_required_or_50x()
        def view(request, exc):
            raise exc

        self.func = view
        self.fake_request = RequestFactory().get('/')

    def test_exceptions(self):
        for exc in ES_EXCEPTIONS:
            response = self.func(self.fake_request, exc(Exception))
            eq_(response.status_code, 503)

    @override_settings(ES_DISABLED=True)
    def test_es_disabled(self):
        response = self.func(self.fake_request)
        eq_(response.status_code, 501)
