import logging
from operator import itemgetter

from pyes import ES, VERSION


log = logging.getLogger('elasticutils')


DEFAULT_HOSTS = ['localhost:9200']
DEFAULT_TIMEOUT = 5
DEFAULT_DOCTYPES = None
DEFAULT_INDEXES = 'default'
DEFAULT_DUMP_CURL = None


def _split(s):
    if '__' in s:
        return s.rsplit('__', 1)
    return s, None


def get_es(hosts=None, default_indexes=None, timeout=None, dump_curl=None,
           **settings):
    """Create an ES object and return it.

    :arg hosts: list of uris; ES hosts to connect to, defaults to
        ``['localhost:9200']``
    :arg default_indexes: list of strings; the default indexes to use,
        defaults to 'default'
    :arg timeout: int; the timeout in seconds, defaults to 5
    :arg dump_curl: function or None; function that dumps curl output,
        see docs, defaults to None
    :arg settings: other settings to pass into `pyes.es.ES`

    Examples:

    >>> get_es()
    >>> get_es(hosts=['localhost:9200'])
    >>> get_es(timeout=30)  # good for indexing
    >>> get_es(default_indexes=['sumo_prod_20120627']
    >>> class CurlDumper(object):
    ...     def write(self, text):
    ...         print text
    ...
    >>> get_es(dump_curl=CurlDumper())

    """
    # Cheap way of de-None-ifying things
    hosts = hosts or DEFAULT_HOSTS
    default_indexes = default_indexes or DEFAULT_INDEXES
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    dump_curl = dump_curl or DEFAULT_DUMP_CURL

    if not isinstance(default_indexes, list):
        default_indexes = [default_indexes]

    es = ES(hosts,
            default_indexes=default_indexes,
            timeout=timeout,
            dump_curl=dump_curl,
            **settings)

    # pyes 0.15 does this lame thing where it ignores dump_curl in
    # the ES constructor and always sets it to None. So what we do
    # is set it manually after the ES has been created and
    # defaults['dump_curl'] is truthy. This might not work for all
    # values of dump_curl.
    if VERSION[0:2] == (0, 15) and dump_curl is not None:
        es.dump_curl = dump_curl

    return es


class InvalidFieldActionError(Exception):
    """Raise this when the field action doesn't exist"""
    pass


def _process_filters(filters):
    rv = []
    for f in filters:
        if isinstance(f, F):
            if f.filters:
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
            else:
                raise InvalidFieldActionError(
                    '%s is not a valid field action' % field_action)
    return rv


class F(object):
    """
    Filter objects.
    """
    def __init__(self, **filters):
        """Creates an F

        :raises InvalidFieldActionError: if the field action is not
            valid

        """
        if filters:
            items = _process_filters(filters.items())
            if len(items) > 1:
                self.filters = {'and': items}
            else:
                self.filters = items[0]
        else:
            self.filters = {}

    def _combine(self, other, conn='and'):
        """
        OR and AND will create a new F, with the filters from both F
        objects combined with the connector `conn`.
        """
        f = F()
        if not self.filters:
            f.filters = other.filters
        elif not other.filters:
            f.filters = self.filters
        elif conn in self.filters:
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
        if (len(self.filters) < 2 and
           'not' in self.filters and 'filter' in self.filters['not']):
            f.filters = self.filters['not']['filter']
        else:
            f.filters = {'not': {'filter': self.filters}}
        return f


# Number of results to show before truncating when repr(S)
REPR_OUTPUT_SIZE = 20


class S(object):
    """
    Represents a lazy ElasticSearch lookup, with a similar api to
    Django's QuerySet.
    """
    def __init__(self, type_=None):
        """Create and return an S.

        :arg type_: class; the model that this S is based on

        """
        self.type = type_
        self.steps = []
        self.start = 0
        self.stop = None
        self.as_list = self.as_dict = False
        self._results_cache = None

    def __repr__(self):
        data = list(self)[:REPR_OUTPUT_SIZE + 1]
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def _clone(self, next_step=None):
        new = self.__class__(self.type)
        new.steps = list(self.steps)
        if next_step:
            new.steps.append(next_step)
        new.start = self.start
        new.stop = self.stop
        return new

    def es(self, **settings):
        """Return a new S with specified ES settings.

        This allows you to configure the ES that gets used to execute
        the search.

        :arg settings: the settings you'd use to build the ES---same
            as what you'd pass to :fun:`get_es`.

        """
        return self._clone(next_step=('es', settings))

    def es_builder(self, builder_function):
        """Return a new S with specified ES builder.

        When you do something with an S that causes it to execute a
        search, then it will call the specified builder function with
        the S instance. The builder function will return an ES object
        that the S will use to execute the search with.

        :arg builder_function: function; takes an S instance and returns
            an ES

        This is handy for caching ES instances. For example, you could
        create a builder that caches ES instances thread-local::

            from threading import local
            _local = local()

            def thread_local_builder(searcher):
                if not hasattr(_local, 'es'):
                    _local.es = get_es()
                return _local.es

            searcher = S.es_builder(thread_local_builder)

        This is also handy for building ES instances with
        configuration defined in a config file.

        """
        return self._clone(next_step=('es_builder', builder_function))

    def indexes(self, *indexes):
        """
        Return a new S instance that will search specified indexes.
        """
        return self._clone(next_step=('indexes', indexes))

    def doctypes(self, *doctypes):
        """
        Return a new S instance that will search specified doctypes.

        .. Note::

           ElasticSearch calls these "mapping types". It's the name
           associated with a mapping.
        """
        return self._clone(next_step=('doctypes', doctypes))

    def values_list(self, *fields):
        """
        Return a new S instance that returns ListSearchResults.
        """
        return self._clone(next_step=('values_list', fields))

    def values_dict(self, *fields):
        """
        Return a new S instance that returns DictSearchResults.
        """
        return self._clone(next_step=('values_dict', fields))

    def order_by(self, *fields):
        """
        Return a new S instance with the ordering changed.
        """
        return self._clone(next_step=('order_by', fields))

    def query(self, **kw):
        """
        Return a new S instance with query args combined with existing
        set.
        """
        return self._clone(next_step=('query', kw.items()))

    def filter(self, *filters, **kw):
        """
        Return a new S instance with filter args combined with
        existing set.
        """
        return self._clone(next_step=('filter', list(filters) + kw.items()))

    def facet(self, **kw):
        """
        Return a new S instance with facet args combined with existing
        set.
        """
        return self._clone(next_step=('facet', kw.items()))

    def extra(self, **kw):
        """
        Return a new S instance with extra args combined with existing
        set.
        """
        new = self._clone()
        actions = 'values_list values_dict order_by query filter facet'.split()
        for key, vals in kw.items():
            assert key in actions
            if hasattr(vals, 'items'):
                new.steps.append((key, vals.items()))
            else:
                new.steps.append((key, vals))
        return new

    def count(self):
        """
        Return the number of hits for the search as an integer.
        """
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
        """
        Loop self.steps to build the query format that will be sent to
        ElasticSearch, and return it as a dict.
        """
        filters = []
        queries = []
        sort = []
        fields = set(['id'])
        facets = {}
        as_list = as_dict = False
        for action, value in self.steps:
            if action == 'order_by':
                sort = []
                for key in value:
                    if key.startswith('-'):
                        sort.append({key[1:]: 'desc'})
                    else:
                        sort.append(key)
            elif action == 'values_list':
                fields |= set(value)
                as_list, as_dict = True, False
            elif action == 'values_dict':
                if not value:
                    fields = set()
                else:
                    fields |= set(value)
                as_list, as_dict = False, True
            elif action == 'query':
                queries.extend(self._process_queries(value))
            elif action == 'filter':
                filters.extend(_process_filters(value))
            elif action == 'facet':
                facets.update(value)
            elif action in ('es_builder', 'es', 'indexes', 'doctypes'):
                # Ignore these--we use these elsewhere, but want to
                # make sure lack of handling it here doesn't throw an
                # error.
                pass
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
            qs['fields'] = list(fields)
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
        """
        Perform the search, then convert that raw format into a
        SearchResults instance and return it.
        """
        if not self._results_cache:
            hits = self.raw()
            if self.as_list:
                ResultClass = ListSearchResults
            elif self.as_dict or self.type is None:
                ResultClass = DictSearchResults
            else:
                ResultClass = ObjectSearchResults
            self._results_cache = ResultClass(self.type, hits, self.fields)
        return self._results_cache

    def get_es(self, default_builder=get_es):
        # The last one overrides earlier ones.
        for action, value in reversed(self.steps):
            if action == 'es_builder':
                # es_builder overrides es
                return value(self)
            elif action == 'es':
                return get_es(**value)

        return default_builder()

    def get_indexes(self, default_indexes=DEFAULT_INDEXES):
        for action, value in reversed(self.steps):
            if action == 'indexes':
                return value

        return default_indexes

    def get_doctypes(self, default_doctypes=DEFAULT_DOCTYPES):
        for action, value in reversed(self.steps):
            if action == 'doctypes':
                return value
        return default_doctypes

    def raw(self):
        """
        Build query and passes to ElasticSearch, then returns the raw
        format returned.
        """
        qs = self._build_query()
        es = self.get_es()
        try:
            hits = es.search(qs, self.get_indexes(), self.get_doctypes())
        except Exception:
            log.error(qs)
            raise
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

            # itemgetter returns an item--not a tuple of one item--if
            # there is only one thing in self.fields. Since we want
            # this to always return a list of tuples, we need to fix
            # that case here.
            if len(self.fields) == 1:
                objs = [(obj,) for obj in objs]
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

