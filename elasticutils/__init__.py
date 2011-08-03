import logging
from functools import wraps
from threading import local

from pyes import ES, exceptions

try:
    from statsd import statsd
except ImportError:
    statsd = None

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


def _split(string):
    if '__' in string:
        return string.rsplit('__', 1)
    else:
        return string, None


def _process_filters(filters):
    rv = []
    log.debug(filters)
    for f in filters:
        log.debug(f)
        if isinstance(f, F):
            log.debug('is an F()')
            rv.append(f.filters)
        else:
            key, val = f
            key, field_action = _split(key)
            if key == 'or_':
                rv.append({'or':_process_filters(val.items())})
            elif field_action is None:
                rv.append({'term': {key: val}})
            elif field_action == 'in':
                rv.append({'in': {key: val}})
            elif field_action in ('gt', 'gte', 'lt', 'lte'):
                rv.append({'range': {key: {field_action: val}}})
    return rv

class F(object):
    """
    Filter objects.
    """
    def __init__(self, **filters):
        self.filters = {'and': _process_filters(filters.items())} if filters \
                else {}

    def _combine(self, other, conn='and'):
        f = F()
        if conn in self.filters:
            f.filters = self.filters
            f.filters[conn].append(other.filters)
        elif conn in other.filters:
            f.filters = other.filters
            f.filters[conn].append(self.filters)
        else:
            f.filters = {conn: [self.filters, other.filters]}
        return f

    def __or__(self, other):
        return self._combine(other, 'or')

    def __and__(self, other):
        return self._combine(other, 'and')

    def __invert__(self):
        f = F()
        f.filters = {'not': {'filter': self.filters}}
        return f


class S(object):

    def __init__(self, type_):
        self.type = type_
        self.steps = []
        self.start = 0
        self.stop = None
        self.as_list = self.as_dict = False
        self._results_cache = None

    def _clone(self, next_step=None):
        new = self.__class__(self.type)
        new.steps = list(self.steps)
        if next_step:
            new.steps.append(next_step)
        new.start = self.start
        new.stop = self.stop
        return new

    def values(self, *fields):
        return self._clone(next_step=('values', fields))

    def values_dict(self, *fields):
        return self._clone(next_step=('values_dict', fields))

    def order_by(self, *fields):
        return self._clone(next_step=('order_by', fields))

    def query(self, **kw):
        return self._clone(next_step=('query', kw.items()))

    def filter(self, *filters, **kw):
        return self._clone(next_step=('filter', list(filters) + kw.items()))

    def facet(self, **kw):
        return self._clone(next_step=('facet', kw.items()))

    def extra(self, **kw):
        new = self._clone()
        actions = 'values values_dict order_by query filter facet'.split()
        for key, vals in kw.items():
            assert key in actions
            if hasattr(vals, 'items'):
                new.steps.append((key, vals.items()))
            else:
                new.steps.append((key, vals))
        return new

    def count(self):
        if self._results_cache:
            return self._results_cache.count
        else:
            return self[:0].raw()['hits']['total']

    def __len__(self):
        return len(self._do_search())

    def __getitem__(self, k):
        new = self._clone()
        # TODO: validate numbers and ranges
        if isinstance(k, slice):
            new.start, new.stop = k.start or 0, k.stop
            return new
        else:
            new.start, new.stop = k, k + 1
            return list(new)[0]

    def _build_query(self):
        filters = []
        queries = []
        sort = []
        fields = ['id']
        facets = {}
        as_list = as_dict = False
        for action, value in self.steps:
            if action == 'order_by':
                for key in value:
                    if key.startswith('-'):
                        sort.append({key[1:]: 'desc'})
                    else:
                        sort.append(key)
            elif action == 'values':
                fields.extend(value)
                as_list, as_dict = True, False
            elif action == 'values_dict':
                if not value:
                    fields = []
                else:
                    fields.extend(value)
                as_list, as_dict = False, True
            elif action == 'query':
                queries.extend(self._process_queries(value))
            elif action == 'filter':
                filters.extend(_process_filters(value))
            elif action == 'facet':
                facets.update(value)
            else:
                raise NotImplementedError(action)

        qs = {}
        if len(filters) > 1:
            qs['filter'] = {'and': filters}
        elif filters:
            qs['filter'] = filters[0]

        if len(queries) > 1:
            qs['query'] = {'bool': {'must': queries}}
        elif queries:
            qs['query'] = queries[0]

        if fields:
            qs['fields'] = fields
        if facets:
            qs['facets'] = facets
            # Copy filters into facets. You probably wanted this.
            for facet in facets.values():
                if 'facet_filter' not in facet and filters:
                    facet['facet_filter'] = qs['filter']
        if sort:
            qs['sort'] = sort
        if self.start:
            qs['from'] = self.start
        if self.stop is not None:
            qs['size'] = self.stop - self.start

        self.fields, self.as_list, self.as_dict = fields, as_list, as_dict
        return qs

    def _process_queries(self, value):
        rv = []
        value = dict(value)
        or_ = value.pop('or_', [])
        for key, val in value.items():
            key, field_action = _split(key)
            if field_action is None:
                rv.append({'term': {key: val}})
            elif field_action == 'text':
                rv.append({'text': {key: val}})
            elif field_action == 'startswith':
                rv.append({'prefix': {key: val}})
            elif field_action in ('gt', 'gte', 'lt', 'lte'):
                rv.append({'range': {key: {field_action: val}}})
            elif field_action == 'fuzzy':
                rv.append({'fuzzy': {key: val}})
        if or_:
            rv.append({'bool': {'should': self._process_queries(or_.items())}})
        return rv

    def _do_search(self):
        if not self._results_cache:
            hits = self.raw()
            if self.as_dict:
                ResultClass = DictSearchResults
            elif self.as_list:
                ResultClass = ListSearchResults
            else:
                ResultClass = ObjectSearchResults
            self._results_cache = ResultClass(self.type, hits, self.fields)
        return self._results_cache

    def raw(self):
        qs = self._build_query()
        es = get_es()
        try:
            hits = es.search(qs, settings.ES_INDEX, self.type._meta.db_table)
        except Exception:
            log.error(qs)
            raise
        if statsd:
            statsd.timing('search', hits['took'])
        log.debug('[%s] %s' % (hits['took'], qs))
        return hits

    def __iter__(self):
        return iter(self._do_search())

    def raw_facets(self):
        return self._do_search().results.get('facets', {})

    @property
    def facets(self):
        facets = {}
        for key, val in self.raw_facets().items():
            if val['_type'] == 'terms':
                facets[key] = [v for v in val['terms']]
            elif val['_type'] == 'range':
                facets[key] = [v for v in val['ranges']]
        return facets


class SearchResults(object):

    def __init__(self, type, results, fields):
        self.type = type
        self.took = results['took']
        self.count = results['hits']['total']
        self.results = results
        self.fields = fields
        self.set_objects(results['hits']['hits'])

    def set_objects(self, hits):
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.objects)

    def __len__(self):
        return len(self.objects)


class DictSearchResults(SearchResults):

    def set_objects(self, hits):
        key = 'fields' if self.fields else '_source'
        self.objects = [r[key] for r in hits]


class ListSearchResults(SearchResults):

    def set_objects(self, hits):
        if self.fields:
            getter = itemgetter(*self.fields)
            objs = [getter(r['fields']) for r in hits]
        else:
            objs = [r['_source'].values() for r in hits]
        self.objects = objs


class ObjectSearchResults(SearchResults):

    def set_objects(self, hits):
        self.ids = [int(r['_id']) for r in hits]
        self.objects = self.type.objects.filter(id__in=self.ids)

    def __iter__(self):
        objs = dict((obj.id, obj) for obj in self.objects)
        return (objs[id] for id in self.ids if id in objs)

