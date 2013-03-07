import copy
import logging
from operator import itemgetter

from pyes import ES
from pyes import VERSION as PYES_VERSION

from elasticutils._version import __version__


log = logging.getLogger('elasticutils')


DEFAULT_HOSTS = ['localhost:9200']
DEFAULT_TIMEOUT = 5
DEFAULT_DOCTYPES = ['document']
DEFAULT_INDEXES = ['default']
DEFAULT_DUMP_CURL = None


class InvalidFieldActionError(Exception):
    """Raise this when the field action doesn't exist"""
    pass


class InvalidFacetType(Exception):
    """Raise when _type is unrecognized."""
    pass


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

    >>> es = get_es()


    >>> es = get_es(hosts=['localhost:9200'])


    >>> es = get_es(timeout=30)  # good for indexing


    >>> es = get_es(default_indexes=['sumo_prod_20120627']


    >>> class CurlDumper(object):
    ...     def write(self, text):
    ...         print text
    ...
    >>> es = get_es(dump_curl=CurlDumper())

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
    if PYES_VERSION[0:2] == (0, 15) and dump_curl is not None:
        es.dump_curl = dump_curl

    return es


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
                rv.append({'or': _process_filters(val.items())})
            elif field_action is None:
                if val is None:
                    rv.append({'missing': {'field': key, "null_value": True}})
                else:
                    rv.append({'term': {key: val}})
            elif field_action in ('startswith', 'prefix'):
                rv.append({'prefix': {key: val}})
            elif field_action == 'in':
                rv.append({'in': {key: val}})
            elif field_action in ('gt', 'gte', 'lt', 'lte'):
                rv.append({'range': {key: {field_action: val}}})
            else:
                raise InvalidFieldActionError(
                    '%s is not a valid field action' % field_action)
    return rv


def _process_facets(facets, flags):
    rv = {}
    for fieldname in facets:
        facet_type = {'terms': {'field': fieldname}}
        if flags.get('global_'):
            facet_type['global'] = flags['global_']
        elif flags.get('filtered'):
            # Note: This is an indicator that the facet_filter should
            # get filled in later when we know all the filters.
            facet_type['facet_filter'] = None

        rv[fieldname] = facet_type
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

        self_filters = copy.deepcopy(self.filters)
        other_filters = copy.deepcopy(other.filters)

        if not self.filters:
            f.filters = other_filters
        elif not other.filters:
            f.filters = self_filters
        elif conn in self.filters:
            f.filters = self_filters
            f.filters[conn].append(other_filters)
        elif conn in other.filters:
            f.filters = other_filters
            f.filters[conn].append(self_filters)
        else:
            f.filters = {conn: [self_filters, other_filters]}

        return f

    def __or__(self, other):
        return self._combine(other, 'or')

    def __and__(self, other):
        return self._combine(other, 'and')

    def __invert__(self):
        f = F()
        self_filters = copy.deepcopy(self.filters)
        if (len(self_filters) < 2
            and 'not' in self_filters
            and 'filter' in self_filters['not']):
            f.filters = self_filters['not']['filter']
        else:
            f.filters = {'not': {'filter': self_filters}}
        return f


# Number of results to show before truncating when repr(S)
REPR_OUTPUT_SIZE = 20


def _boosted_value(name, action, key, value, boost):
    """Boost a value if we should in _process_queries"""
    if boost is not None:
        # Note: Most queries use 'value' for the key name except Text
        # queries which use 'query'. So we have to do some switcheroo
        # for that.
        value_key = 'query' if action in ['text', 'text_phrase'] else 'value'
        return {name: {'boost': boost, value_key: value}}
    return {name: value}


# Maps ElasticUtils field actions to their ElasticSearch query names.
ACTION_MAP = {
    None: 'term',  # Default to term
    'in': 'in',
    'term': 'term',
    'startswith': 'prefix',  # Backwards compatability
    'prefix': 'prefix',
    'text': 'text',
    'text_phrase': 'text_phrase',
    'fuzzy': 'fuzzy'}


class S(object):
    """Represents a lazy ElasticSearch Search API request.

    The API for `S` takes inspiration from Django's QuerySet.

    `S` can be either typed or untyped. An untyped `S` returns dict
    results by default.

    An `S` is lazy in the sense that it doesn't do an ElasticSearch
    search request until it's forced to evaluate by either iterating
    over it, calling ``.count``, doing ``len(s)``, or calling
    ``.facet_count``.

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
        self.field_boosts = {}
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
        new.field_boosts = self.field_boosts.copy()
        return new

    def es(self, **settings):
        """Return a new S with specified ES settings.

        This allows you to configure the ES that gets used to execute
        the search.

        :arg settings: the settings you'd use to build the ES---same
            as what you'd pass to :py:func:`get_es`.

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

    def explain(self, value=True):
        """
        Return a new S instance with explain set.
        """
        return self._clone(next_step=('explain', value))

    def values_list(self, *fields):
        """
        Return a new S instance that returns ListSearchResults.

        :arg fields: the list of fields to have in the results.
            By default this is at least ``['id']``.

        """
        return self._clone(next_step=('values_list', fields))

    def values_dict(self, *fields):
        """
        Return a new S instance that returns DictSearchResults.

        :arg fields: the list of fields to have in the results.
            By default, this won't specify fields and thus ES
            will return everything.

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

    def boost(self, **kw):
        """
        Return a new S instance with field boosts.
        """
        new = self._clone()
        new.field_boosts.update(kw)
        return new

    def demote(self, amount_, **kw):
        """
        Returns a new S instance with boosting query and demotion.
        """
        return self._clone(next_step=('demote', (amount_, kw)))

    def facet(self, *args, **kw):
        """
        Return a new S instance with facet args combined with existing
        set.
        """
        return self._clone(next_step=('facet', (args, kw)))

    def facet_raw(self, **kw):
        """
        Return a new S instance with raw facet args combined with
        existing set.
        """
        return self._clone(next_step=('facet_raw', kw.items()))

    def highlight(self, *fields, **kwargs):
        """Set highlight/excerpting with specified options.

        This highlight will override previous highlights.

        This won't let you clear it--we'd need to write a
        ``clear_highlight()``.

        :arg fields: The list of fields to highlight. If the field is
            None, then the highlight is cleared.

        Additional keyword options:

        * ``pre_tags`` -- List of tags before highlighted portion
        * ``post_tags`` -- List of tags after highlighted portion

        See ElasticSearch highlight:

        http://www.elasticsearch.org/guide/reference/api/search/highlighting.html

        """
        # TODO: Implement `limit` kwarg if useful.
        # TODO: Once oedipus is no longer needed in SUMO, support ranked lists
        # of before_match and after_match tags. ES can highlight more
        # significant stuff brighter.
        return self._clone(next_step=('highlight', (fields, kwargs)))

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
        dict_fields = set()
        list_fields = set()
        facets = {}
        facets_raw = {}
        demote = None
        highlight_fields = set()
        highlight_options = {}
        explain = False
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
                if not value:
                    list_fields = set()
                else:
                    list_fields |= set(value)
                as_list, as_dict = True, False
            elif action == 'values_dict':
                if not value:
                    dict_fields = set()
                else:
                    dict_fields |= set(value)
                as_list, as_dict = False, True
            elif action == 'explain':
                explain = value
            elif action == 'query':
                queries.extend(self._process_queries(value))
            elif action == 'demote':
                demote = (value[0], self._process_queries(value[1]))
            elif action == 'filter':
                filters.extend(_process_filters(value))
            elif action == 'facet':
                # value here is a (args, kwargs) tuple
                facets.update(_process_facets(*value))
            elif action == 'facet_raw':
                facets_raw.update(dict(value))
            elif action == 'highlight':
                if value[0] == (None,):
                    highlight_fields = set()
                else:
                    highlight_fields |= set(value[0])
                highlight_options.update(value[1])
            elif action in ('es_builder', 'es', 'indexes', 'doctypes', 'boost'):
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

        if demote is not None:
            qs['query'] = {
                'boosting': {
                    'positive': qs['query'],
                    'negative': demote[1],
                    'negative_boost': demote[0]
                    }
                }

        if as_list and list_fields:
            fields = qs['fields'] = list(list_fields)
        elif as_dict and dict_fields:
            fields = qs['fields'] = list(dict_fields)
        else:
            fields = set()

        if facets:
            qs['facets'] = facets
            # Hunt for `facet_filter` shells and update those. We use
            # None as a shell, so if it's explicitly set to None, then
            # we update it.
            for facet in facets.values():
                if facet.get('facet_filter', 1) is None:
                    facet['facet_filter'] = qs['filter']

        if facets_raw:
            qs.setdefault('facets', {}).update(facets_raw)

        if sort:
            qs['sort'] = sort
        if self.start:
            qs['from'] = self.start
        if self.stop is not None:
            qs['size'] = self.stop - self.start

        if highlight_fields:
            qs['highlight'] = self._build_highlight(
                highlight_fields, highlight_options)

        if explain:
            qs['explain'] = True

        self.fields, self.as_list, self.as_dict = fields, as_list, as_dict
        return qs

    def _build_highlight(self, fields, options):
        """Return the portion of the query that controls highlighting."""
        ret = {'fields': dict((f, {}) for f in fields),
               'order': 'score'}
        ret.update(options)
        return ret

    def _process_queries(self, value):
        rv = []
        value = dict(value)
        or_ = value.pop('or_', [])
        for key, val in value.items():
            field_name, field_action = _split(key)

            # Boost by name__action overrides boost by name.
            boost = self.field_boosts.get(key)
            if boost is None:
                boost = self.field_boosts.get(field_name)

            if field_action in ACTION_MAP:
                rv.append(
                    {ACTION_MAP[field_action]: _boosted_value(
                            field_name, field_action, key, val, boost)})

            elif field_action == 'query_string':
                # query_string has different syntax, so it's handled
                # differently.
                #
                # Note: query_string queries are not boosted with
                # .boost()---they're boosted in the query text itself.
                rv.append(
                    {'query_string':
                         {'default_field': field_name,
                          'query': val}})

            elif field_action in ('gt', 'gte', 'lt', 'lte'):
                # Ranges are special and have a different syntax, so
                # we handle them separately.
                rv.append(
                    {'range': {field_name: _boosted_value(
                                field_name, field_action, key, val, boost)}})

            else:
                raise InvalidFieldActionError(
                    '%s is not a valid field action' % field_action)

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
            elif self.as_dict:
                ResultClass = DictSearchResults
            else:
                ResultClass = ObjectSearchResults
            self._results_cache = ResultClass(self.type, hits, self.fields)
        return self._results_cache

    def get_es(self, default_builder=get_es):
        """Returns the ES object to use."""
        # The last one overrides earlier ones.
        for action, value in reversed(self.steps):
            if action == 'es_builder':
                # es_builder overrides es
                return value(self)
            elif action == 'es':
                return get_es(**value)

        return default_builder()

    def get_indexes(self, default_indexes=DEFAULT_INDEXES):
        """Returns the list of indexes to act on."""
        for action, value in reversed(self.steps):
            if action == 'indexes':
                return list(value)

        if self.type is not None:
            indexes = self.type.get_index()
            if isinstance(indexes, basestring):
                indexes = [indexes]
            return indexes

        return default_indexes

    def get_doctypes(self, default_doctypes=DEFAULT_DOCTYPES):
        """Returns the list of doctypes to use."""
        for action, value in reversed(self.steps):
            if action == 'doctypes':
                return list(value)

        if self.type is not None:
            return [self.type.get_mapping_type_name()]

        return default_doctypes

    def raw(self):
        """
        Build query and passes to ElasticSearch, then returns the raw
        format returned.
        """
        qs = self._build_query()
        es = self.get_es()

        hits = es.search(qs, self.get_indexes(), self.get_doctypes())

        log.debug('[%s] %s' % (hits['took'], qs))
        return hits

    def __iter__(self):
        return iter(self._do_search())

    def _raw_facets(self):
        return self._do_search().results.get('facets', {})

    def facet_counts(self):
        facets = {}
        for key, val in self._raw_facets().items():
            if val['_type'] == 'terms':
                facets[key] = [v for v in val['terms']]
            elif val['_type'] == 'range':
                facets[key] = [v for v in val['ranges']]
            elif val['_type'] == 'date_histogram':
                facets[key] = [v for v in val['entries']]
            elif val['_type'] == 'histogram':
                facets[key] = [v for v in val['entries']]
            else:
                raise InvalidFacetType(
                    'Facet _type "%s". key "%s" val "%r"' %
                    (val['_type'], key, val))
        return facets


class MLT(object):
    """Represents a lazy ElasticSearch More Like This API request.

    This is lazy in the sense that it doesn't evaluate and execute the
    ElasticSearch request unless you force it to by iterating over it
    or getting the length of the search results.

    For example::

    >>> mlt = MLT(2034, index='addons_index', doctype='addon')
    >>> num_related_documents = len(mlt)
    >>> num_related_documents = list(mlt)

    """
    def __init__(self, id_, s=None, fields=None, index=None, doctype=None,
                 es=None, **query_params):
        """
        When the MLT is evaluated, it generates a list of dict results.

        :arg id_: The id of the document we want to find more like.
        :arg s: An instance of an S. The query is passed in the body of
            the more like this request.
        :arg fields: A list of fields to use for more like this.
        :arg index: The index to use. Falls back to the first index
            listed in s.
        :arg doctype: The doctype to use. Falls back to the first
            doctype listed in s.
        :arg es: The ES object to use. If you don't provide one, then it
            will create one for you.
        :arg query_params: Any additional query parameters for the
            more like this call.

        .. Note::

           You must specify either an `s` or the `index` and `doctype`
           arguments. Omitting them will result in a `ValueError`.

        """
        # You have to provide either an s OR an index and a doc_type.
        if s is None and (index is None or doctype is None):
            raise ValueError(
                'Either you must provide a valid s or index and doc_type')

        self.s = s
        if s is not None:
            # If an index or doctype isn't given, we use the first one
            # in the S.
            self.index = index or s.get_indexes()[0]
            self.doctype = doctype or s.get_doctypes()[0]
            self.type = s.type
        else:
            self.index = index
            self.doctype = doctype
            self.type = None

        self.id = id_
        self.fields = fields
        self.es = es
        self.query_params = query_params
        self._results_cache = None

    def __iter__(self):
        return iter(self._do_search())

    def __len__(self):
        return len(self._do_search())

    def get_es(self):
        """Returns an ES

        * If there's an s, then it returns that ES.
        * If the es was provided in the constructor, then it returns that ES.
        * Otherwise, it creates a new ES and returns that.

        Override this if that behavior isn't correct for you.

        """
        if self.s:
            return self.s.get_es()

        return self.es or get_es()

    def raw(self):
        """
        Build query and passes to ElasticSearch, then returns the raw
        format returned.
        """
        es = self.get_es()

        kwargs = {}
        path = es._make_path([self.index, self.doctype, self.id, '_mlt'])

        params = dict(self.query_params)

        if self.fields and 'mlt_fields' not in params:
            params['mlt_fields'] = ','.join(self.fields)
        kwargs['params'] = params

        if self.s:
            kwargs['body'] = self.s._build_query()

        hits = es._send_request('GET', path, **kwargs)
        log.debug(hits)

        log.debug('[%s] %s' % (hits['took'], kwargs))
        return hits

    def _do_search(self):
        """
        Perform the mlt call, then convert that raw format into a
        SearchResults instance and return it.
        """
        if not self._results_cache:
            hits = self.raw()
            self._results_cache = DictSearchResults(self.type, hits, None)
        return self._results_cache


class SearchResults(object):
    def __init__(self, type, results, fields):
        self.type = type
        self.took = results.get('took', 0)
        self.count = results.get('hits', {}).get('total', 0)
        self.results = results
        self.fields = fields
        self.set_objects(results.get('hits', {}).get('hits', []))

    def set_objects(self, hits):
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.objects)

    def __len__(self):
        return len(self.objects)


class DictResult(dict):
    pass


class TupleResult(tuple):
    pass


class DictSearchResults(SearchResults):
    def set_objects(self, hits):
        key = 'fields' if self.fields else '_source'
        self.objects = [decorate_with_metadata(DictResult(r[key]), r)
                        for r in hits]


class ListSearchResults(SearchResults):
    def set_objects(self, hits):
        if self.fields:
            getter = itemgetter(*self.fields)
            objs = [(getter(r['fields']), r) for r in hits]

            # itemgetter returns an item--not a tuple of one item--if
            # there is only one thing in self.fields. Since we want
            # this to always return a list of tuples, we need to fix
            # that case here.
            if len(self.fields) == 1:
                objs = [((obj,), r) for obj, r in objs]
        else:
            objs = [(r['_source'].values(), r) for r in hits]
        self.objects = [decorate_with_metadata(TupleResult(obj), r)
                        for obj, r in objs]


def _convert_results_to_dict(r):
    """Takes a results from ES and returns fields."""
    if 'fields' in r:
        return r['fields']
    if '_source' in r:
        return r['_source']
    return {'id': r['_id']}


class ObjectSearchResults(SearchResults):
    def set_objects(self, hits):
        mapping_type = (self.type if self.type is not None
                        else DefaultMappingType)
        self.objects = [
            decorate_with_metadata(
                mapping_type.from_results(_convert_results_to_dict(r)),
                r)
            for r in hits]

    def __iter__(self):
        return self.objects.__iter__()


def decorate_with_metadata(obj, hit):
    """Return obj decorated with hit-scope metadata."""
    # ES id
    obj._id = hit.get('_id', 0)
    # Source data
    obj._source = hit.get('_source', {})
    # The search result score
    obj._score = hit.get('_score')
    # The document type
    obj._type = hit.get('_type')
    # Explanation structure
    obj._explanation = hit.get('_explanation', {})
    # Highlight bits
    obj._highlight = hit.get('highlight', {})
    return obj


class NoModelError(Exception):
    pass


class MappingType(object):
    """Base class for mapping types.

    To extend this class:

    1. implement ``get_index``.
    2. implement ``get_mapping_type_name``.
    3. if this ties back to a model, implement ``get_model``
       and possibly also ``get_object``.

    """
    def __init__(self):
        self._results_dict = {}
        self._object = None

    @classmethod
    def from_results(cls, results_dict):
        mt = cls()
        mt._results_dict = results_dict
        return mt

    def _get_object_lazy(self):
        if self._object:
            return self._object

        self._object = self.get_object()
        return self._object

    def get_object(self):
        """Returns the model instance

        This gets called when someone uses the ``.object`` attribute
        which triggers lazy-loading of the object.

        If this MappingType is associated with a model, then by
        default, it calls::

            self.get_model().get(id=self._id)

        where ``self._id`` is the ElasticSearch document id.

        Override it to do something different.

        :raises cls.DoesNotExist: if the instance doesn't exist.
            You should wrap this in a try/except block like this::

                try:
                    obj = result.object
                except result.get_model().DoesNotExist:
                    # exception handling here....

        """
        return self.get_model().get(id=self._id)

    @classmethod
    def get_indexes(cls):
        """Returns the indexes to use for this mapping type.

        You can specify the indexes to use for this mapping type.
        This affects ``S`` built with this type.

        By default, this is ["default"].

        Override this if you want something different.

        """
        return DEFAULT_INDEXES

    @classmethod
    def get_mapping_type_name(cls):
        """Returns the mapping type name.

        You can specify the mapping type name (also sometimes called the
        document type) with this method.

        By default, this is None.

        Override this if you want something different.

        """
        return DEFAULT_DOCTYPES

    @classmethod
    def get_model(cls):
        """Return the model related to this MappingType.

        This can be any class that has an instance related to this
        Mappingtype by id.

        By default, raises NoModelError.

        Override this to return a class that has a ``.get(id=id)``
        classmethod.

        TODO: fix the docs.

        """
        raise NoModelError

    # Simulate attribute access

    def __getattr__(self, name):
        if name in self.__dict__:
            # We want instance/class attributes to take precedence.
            # So if something like that exists, we raise an
            # AttributeError and Python handles it.
            raise AttributeError

        if name == 'object':
            # 'object' is lazy-loading. We don't do this with a
            # property because Python sucks at properties and
            # subclasses.
            return self.get_object()

        # If that doesn't exist, then check the results_dict.
        if name in self._results_dict:
            return self._results_dict[name]

        raise AttributeError

    # Simulate read-only container access

    def __len__(self):
        return self._results_dict.__len__()

    def __getitem__(self, key):
        return self._results_dict.__getitem__(key)

    def __iter__(self):
        return self._results_dict.__iter__()

    def __reversed__(self):
        return self._results_dict.__reversed__()

    def __contains__(self, item):
        return self._results_dict.__contains__(item)


class DefaultMappingType(MappingType):
    """This is the default mapping type for S."""
