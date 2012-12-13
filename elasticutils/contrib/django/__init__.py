import logging
from functools import wraps

import pyelasticsearch

import elasticutils
from elasticutils import F, InvalidFieldActionError

try:
    from django.conf import settings
    from django.shortcuts import render
except ImportError:
    pass


log = logging.getLogger('elasticutils')


def get_es(**overrides):
    """Return a pyelasticsearch ElasticSearch object using settings
    from ``settings.py``.

    :arg overrides: Allows you to override defaults to create the
    ElasticSearch object.

    You can override any of the arguments listed in :ref:`get_es`.

    For example, if you wanted to create an ElasticSearch with a
    longer timeout to a different cluster, you'd do:

    >>> from elasticutils.contrib.django import get_es
    >>> es = get_es(urls=['http://some_other_cluster:9200'], timeout=30)

    """
    defaults = {
        'urls': settings.ES_URLS,
        'timeout': getattr(settings, 'ES_TIMEOUT', 5)
        }

    defaults.update(overrides)
    return elasticutils.get_es(**defaults)


def es_required(fun):
    """Wrap a callable and return None if ES_DISABLED is False.

    This also adds an additional `es` argument to the callable
    giving you an ElasticSearch to use.

    """
    @wraps(fun)
    def wrapper(*args, **kw):
        if getattr(settings, 'ES_DISABLED', False):
            log.debug('Search disabled for %s.' % fun)
            return

        return fun(*args, es=get_es(), **kw)
    return wrapper


def es_required_or_50x(disabled_template='elasticutils/501.html',
                       error_template='elasticutils/503.html'):
    """Wrap a Django view and handle ElasticSearch errors.

    This wraps a Django view and returns 501 or 503 status codes and
    pages if things go awry.

    HTTP 501
      Returned when ``ES_DISABLED`` is True.

    HTTP 503
      Returned when any of the following exceptions are thrown:

      * pyelasticsearch.exceptions.ConnectionError
      * pyelasticsearch.exceptions.ElasticHttpNotFoundError
      * pyelasticsearch.exceptions.Timeout

      Template variables:

      * error: A string version of the exception thrown.

    :arg disabled_template: The template to use when ES_DISABLED is
        True.

        Defaults to ``elasticutils/501.html``.
    :arg error_template: The template to use when ElasticSearch isn't
        working properly, is missing an index, or something along
        those lines.

        Defaults to ``elasticutils/503.html``.


    Examples::

        # This creates a home_view and decorates it to use the
        # default templates.

        @es_required_or_50x()
        def home_view(request):
            ...


        # This creates a search_view and overrides the templates

        @es_required_or_50x(disabled_template='search/es_disabled.html',
                            error_template('search/es_down.html')
        def search_view(request):
            ...

    """
    def wrap(fun):
        @wraps(fun)
        def wrapper(request, *args, **kw):
            if getattr(settings, 'ES_DISABLED', False):
                response = render(request, disabled_template)
                response.status_code = 501
                return response

            try:
                return fun(request, *args, **kw)

            except (pyelasticsearch.exceptions.ConnectionError,
                    pyelasticsearch.exceptions.ElasticHttpNotFoundError,
                    pyelasticsearch.exceptions.Timeout) as exc:
                response = render(request, error_template, {'error': exc})
                response.status_code = 503
                return response

        return wrapper

    return wrap


class S(elasticutils.S):
    """S that's more Django-focused

    * creates ElasticSearch objects based on ``settings.py`` settings

    """
    def __init__(self, mapping_type):
        """Create and return an S.

        :arg mapping_type: class; the mapping type that this S is based on

        .. Note::

           The :class: `elasticutils.S` doesn't require the
           `mapping_type` argument, but the
           :class:`elasticutils.contrib.django.S` does.

        """
        return super(S, self).__init__(mapping_type)

    def get_es(self, default_builder=get_es):
        """Returns the pyelasticsearch ElasticSearch object to use.

        This uses the django get_es builder by default which takes
        into account settings in ``settings.py``.

        """
        return super(S, self).get_es(default_builder=default_builder)

    def get_indexes(self, default_indexes=None):
        """Returns the list of indexes to act on."""
        doctype = self.type.get_mapping_type_name()
        indexes = (settings.ES_INDEXES.get(doctype) or
                   settings.ES_INDEXES['default'])
        if isinstance(indexes, basestring):
            indexes = [indexes]
        return super(S, self).get_indexes(default_indexes=indexes)

    def get_doctypes(self, default_doctypes=None):
        """Returns the doctypes (or mapping type names) to use."""
        doctypes = self.type.get_mapping_type_name()
        if isinstance(doctypes, basestring):
            doctypes = [doctypes]
        return super(S, self).get_doctypes(default_doctypes=doctypes)
