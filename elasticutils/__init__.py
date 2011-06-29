import logging
from functools import wraps
from threading import local

from pyes import ES

try:
    from django.conf import settings
except ImportError:
    import es_settings as settings


_local = local()
log = logging.getLogger('elasticsearch')


def get_es():
    """Return one es object."""
    if not hasattr(_local, 'es'):
        timeout = getattr(settings, 'ES_TIMEOUT', 1)
        _local.es = ES(settings.ES_HOSTS, default_indexes=[settings.ES_INDEX],
                       timeout=timeout)
    return _local.es


def es_required(f):
    @wraps(f)
    def wrapper(*args, **kw):
        if settings.ES_DISABLED:
            log.debug('Search disabled for %s.' % f)
            return

        return f(*args, es=get_es(), **kw)
    return wrapper


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
        self.type = type
        self.total = None
        self.result_transform = result_transform
        self.offset = 0

    def _clone(self):
        new = self.__class__(self.type)
        new.filter_ = self.filter_
        new.results = list(self.results)
        new.facets = dict(self.facets)
        new.objects = list(self.objects)
        new.ordering = list(self.ordering)
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

    def order_by(self, *fields):
        new = self._clone()
        for field in fields:
            if field.startswith('-'):
                new.ordering.append({field[1:]: 'desc'})
            else:
                new.ordering.append(field)
        return new

    def execute(self, start=0, stop=None):
        es = get_es()
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

        self.offset = query.get('from', 0)
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
