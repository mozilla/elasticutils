import logging
from functools import wraps
from threading import local

import pyes
from pyes.es import thrift_enable

import elasticutils
from elasticutils import F, InvalidFieldActionError

try:
    from django.conf import settings
    from django.shortcuts import render
except ImportError:
    pass

try:
    from statsd import statsd
except ImportError:
    statsd = None


log = logging.getLogger('elasticutils')


_local = local()
_local.disabled = {}


def get_es(**overrides):
    """Return an ES object using settings from settings.py

    :arg overrides: Allows you to override defaults to create the ES.

    Things you can override:

    * default_indexes
    * timeout
    * dump_curl

    Values for these correspond with the arguments to pyes.es.ES.

    For example, if you wanted to create an ES for indexing with a timeout
    of 30 seconds, you'd do:

    >>> from elasticutils.contrib.django import get_es
    >>> es = get_es(timeout=30)

    If you wanted to create an ES for debugging that dumps curl
    commands to stdout, you could do:

    >>> class CurlDumper(object):
    ...     def write(self, s):
    ...         print s
    ...
    >>> from elasticutils.contrib.django import get_es
    >>> es = get_es(dump_curl=CurlDumper())
    """
    if overrides or not hasattr(_local, 'es'):
        defaults = {
            'default_indexes': [settings.ES_INDEXES['default']],
            'timeout': getattr(settings, 'ES_TIMEOUT', 5),
            'dump_curl': getattr(settings, 'ES_DUMP_CURL', False)
            }

        defaults.update(overrides)
        if (not thrift_enable and
            not settings.ES_HOSTS[0].split(':')[1].startswith('92')):
            raise ValueError('ES_HOSTS is not set to a valid port starting '
                             'with 9200-9299 range. Other ports are valid '
                             'if using pythrift.')
        es = elasticutils.get_es(settings.ES_HOSTS, **defaults)

        # Cache the es if there weren't any overrides.
        if not overrides:
            _local.es = es
    else:
        es = _local.es

    return es


def es_required(fun):
    """Wrap a callable and return None if ES_DISABLED is False.

    This also adds an additional `es` argument to the callable
    giving you an ES to use.

    """
    @wraps(fun)
    def wrapper(*args, **kw):
        if getattr(settings, 'ES_DISABLED', False):
            # Log once.
            if fun.__name__ not in _local.disabled:
                log.debug('Search disabled for %s.' % fun)
                _local.disabled[fun.__name__] = 1
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

      * pyes.urllib3.MaxRetryError: Connection problems with ES.
      * pyes.exceptions.IndexMissingException: When the index is
        missing.
      * pyes.exceptions.ElasticSearchException: Various other
        ElasticSearch related errors.

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

            except (pyes.urllib3.MaxRetryError,
                    pyes.exceptions.IndexMissingException,
                    pyes.exceptions.ElasticSearchException) as exc:
                response = render(request, error_template, {'error': exc})
                response.status_code = 503
                return response

        return wrapper

    return wrap


class S(elasticutils.S):
    """S that's more Django-focused

    * uses an ES that's based on settings
    * if statsd is installed, calls statsd.timing with how long
      it took to do the query

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

    def raw(self):
        hits = super(S, self).raw()
        if statsd:
            statsd.timing('search', hits['took'])
        return hits

    def get_es(self, default_builder=None):
        """Returns the ES to use."""
        # Override the default_builder with the Django one
        return super(S, self).get_es(default_builder=get_es)

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
