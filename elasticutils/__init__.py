import logging
from functools import wraps
from threading import local

from pyes import ES, exceptions

try:
    from django.conf import settings
except ImportError:
    import es_settings as settings


_local = local()
_local.disabled = {}
log = logging.getLogger('elasticsearch')


def get_es():
    """Return one es object."""
    if not hasattr(_local, 'es'):
        timeout = getattr(settings, 'ES_TIMEOUT', 1)
        dump = getattr(settings, 'ES_DUMP_CURL', False)
        _local.es = ES(settings.ES_HOSTS, default_indexes=[settings.ES_INDEX],
                       timeout=timeout, dump_curl=dump)
    return _local.es


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


def _process_filters(filters):
    qfilters = []
    for field, value in filters.iteritems():
        qfilters.append(dict(term={field: value}))

    if len(qfilters) > 1:
        return {'and': qfilters}
    else:
        return qfilters[0]


class F(object):
    """
    Filter objects.
    """
    def __init__(self, **filters):
        self.filters = _process_filters(filters) if filters else {}

    def __or__(self, other):
        f = F()
        if 'or' in self.filters:
            f.filters = self.filters
            f.filters['or'].append(other.filters)
        elif 'or' in other.filters:
            f.filters = other.filters
            f.filters['or'].append(self.filters)
        else:
            f.filters = {'or': [self.filters, other.filters]}
        return f


class S(object):
    def __init__(self, query=None, type=None, result_transform=None,
                 **filters):
        """
        `query` is the string we are querying.
        `type` is the object type we are querying
        `result_transform` is a callable that transforms the results from
            ElasticSearch into a set of objects.
        """
        if isinstance(query, basestring):
            self.query = dict(query_string=dict(query=query))
        elif isinstance(query, dict):
            self.query = query
        else:
            self.query = dict(match_all={})
        if filters:
            filter = _process_filters(filters)
            self.query = dict(filtered=dict(query=self.query, filter=filter))
        self.filter_ = None
        self.results = []
        self.facets = {}
        self.objects = []
        self.ordering = []
        self.score_ = None
        self.type = type
        self.total = None
        self.result_transform = result_transform
        self.offset = 0

    def _clone(self):
        new = self.__class__(self.type)
        new.query = self.query
        new.filter_ = self.filter_
        new.results = list(self.results)
        new.facets = dict(self.facets)
        new.objects = list(self.objects)
        new.ordering = list(self.ordering)
        new.score_ = self.score_
        new.type = self.type
        new.total = self.total
        new.result_transform = self.result_transform
        new.offset = self.offset
        return new

    def filter(self, f=None, **filters):
        """
        Takes either a kwargs of ``and`` filters.  Or it takes an ``F`` object.
        """
        if f:
            self.filter_ = f.filters
        else:
            self.filter_ = _process_filters(filters)

        return self

    def facet(self, field, script=None, global_=False):
        facetdetails = dict(field=field)
        if script:
            facetdetails['script'] = script

        facet = dict(terms=facetdetails)

        if global_:
            facet['global'] = True
        self.facets[field] = facet
        return self

    def score(self, script, params=None):
        """
        Custom score queries allow you to use a script to calculate a score by
        which your results will be ordered (higher scores before lower scores).
        For more information:
        http://www.elasticsearch.org/guide/reference/query-dsl/custom-score-query.html
        """
        self.score_ = dict(script=script, params=params)
        return self

    def order_by(self, *fields):
        new = self._clone()
        for field in fields:
            if field.startswith('-'):
                new.ordering.append({field[1:]: 'desc'})
            else:
                new.ordering.append(field)
        return new

    def _build_query(self, start=0, stop=None):
        query = dict(query=self.query)
        if self.filter_:
            query['filter'] = self.filter_
        if self.facets:
            query['facets'] = self.facets
        if stop:
            query['size'] = stop - start
        if start:
            query['from'] = start
        if self.ordering:
            query['sort'] = self.ordering

        if self.score_:
            query['query'] = dict(custom_score=dict(query=query['query'], script=self.score_['script']))
            if (self.score_['params']):
                query['query']['custom_score']['params'] = self.score_['params']

        return query

    def execute(self, start=0, stop=None):
        es = get_es()
        query = self._build_query(start, stop)
        self.offset = query.get('from', 0);

        self.results = es.search(query, settings.ES_INDEX, self.type)

        if self.result_transform:
            self.objects = self.result_transform(self.results)
        self.total = self.results['hits']['total']
        return self

    def get_results(self, **kw):
        if not self.results:
            self.execute(**kw)
        return self.results['hits']['hits']

    def get_facet(self, key):
        if not self.results:
            self.execute()

        if 'facets' not in self.results:
            return None

        return dict((t['term'], t['count']) for t
                     in self.results['facets'][key]['terms'])

    def __len__(self):
        if not self.results:
            self.execute()

        return self.results['hits']['total']

    def __iter__(self):
        return iter(self.objects)

    def __getitem__(self, k):
        """
        ``__getitem__`` gets the elements specified by doing ``rs[k]`` where
        ``k`` is a slice (e.g. ``1:2``) or an integer.

        ``objects`` doesn't contain all ``total`` items, just the items for
        the current page, so we need to adjust ``k``
        """
        if self.objects:
            start = 0
            stop = None
            if isinstance(k, slice):
                start = k.start
                stop = k.stop
            self.execute(start, stop)

        if isinstance(k, slice) and k.start >= self.offset:
            k = slice(k.start - self.offset, k.stop - self.offset if k.stop
                      else None)
        elif isinstance(k, int):
            k -= self.offset

        return self.objects.__getitem__(k)

    def __str__(self):
        query = self._build_query()
        return str(query)
