import logging
from functools import wraps
from threading import local

from pyes import exceptions
from pyes.es import thrift_enable

import elasticutils
from elasticutils import F, InvalidFieldActionError

try:
    from django.conf import settings
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


def es_required(f):
    @wraps(f)
    def wrapper(*args, **kw):
        if settings.ES_DISABLED:
            # Log once.
            if f.__name__ not in _local.disabled:
                log.debug('Search disabled for %s.' % f)
                _local.disabled[f.__name__] = 1
            return

        return f(*args, es=get_es(), **kw)
    return wrapper


def es_required_or_50x(disabled_msg, error_msg):
    """
    This takes a Django view that requires ElasticSearch.

    If `ES_DISABLED` is `True` then we raise a 501 Not Implemented and display
    the disabled_msg.  If we try the view and an ElasticSearch exception is
    raised we raise a 503 error with the error_msg.

    We use user-supplied templates in elasticutils/501.html and
    elasticutils/503.html.
    """
    def wrap(f):
        @wraps(f)
        def wrapper(request, *args, **kw):
            from django.shortcuts import render
            if settings.ES_DISABLED:
                response = render(request, 'elasticutils/501.html',
                                  {'msg': disabled_msg})
                response.status_code = 501
                return response
            else:
                try:
                    return f(request, *args, **kw)
                except exceptions.ElasticSearchException as error:
                    response = render(request, 'elasticutils/503.html',
                            {'msg': error_msg, 'error': error})
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
    def __init__(self, type_):
        """Create and return an S.

        :arg type_: class; the model that this S is based on

        .. Note::

           The :class: `elasticutils.S` doesn't require the `type_`
           argument, but the :class:`elasticutils.contrib.django.S`
           does.

        """
        return super(S, self).__init__(type_)

    def raw(self):
        hits = super(S, self).raw()
        if statsd:
            statsd.timing('search', hits['took'])
        return hits

    def get_es(self, default_builder=None):
        # Override the default_builder with the Django one
        return super(S, self).get_es(default_builder=get_es)

    def get_indexes(self, default_indexes=None):
        doctype = self.type._meta.db_table
        indexes = (settings.ES_INDEXES.get(doctype) or
                   settings.ES_INDEXES['default'])
        return super(S, self).get_indexes(default_indexes=indexes)

    def get_doctypes(self, default_doctypes=None):
        doctype = self.type._meta.db_table
        return super(S, self).get_doctypes(default_doctypes=doctype)
