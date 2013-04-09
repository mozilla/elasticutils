import copy
import logging
from operator import itemgetter

from pyelasticsearch import ElasticSearch
from pyelasticsearch import __version__ as PYELASTICSEARCH_VERSION

from elasticutils._version import __version__


log = logging.getLogger('elasticutils')


DEFAULT_URLS = ['http://localhost:9200']
DEFAULT_DOCTYPES = None
DEFAULT_INDEXES = None
DEFAULT_TIMEOUT = 5


class ElasticUtilsError(Exception):
    """Base class for ElasticUtils errors."""
    pass


class InvalidFieldActionError(ElasticUtilsError):
    """Raise this when the field action doesn't exist"""
    pass


class InvalidFacetType(ElasticUtilsError):
    """Raise when _type is unrecognized."""
    pass


class BadSearch(ElasticUtilsError):
    """Raise when there is something wrong with the search."""
    pass


def _build_key(urls, timeout, **settings):
    # Order the settings by key and then turn it into a string with
    # repr. There are a lot of edge cases here, but the worst that
    # happens is that the key is different and so you get a new
    # ElasticSearch. We'll probably have to tweak this.
    settings = sorted(settings.items(), key=lambda item: item[0])
    settings = repr([(k, v) for k, v in settings])

    # pyelasticsearch allows urls to be a string, so we make sure to
    # account for that when converting whatever it is into a tuple.
    if isinstance(urls, basestring):
        urls = (urls,)
    else:
        urls = tuple(urls)

    # Generate a tuple of all the bits and return that as the key
    # because that's hashable.
    key = (urls, timeout, settings)
    return key


_cached_elasticsearch = {}


def get_es(urls=None, timeout=DEFAULT_TIMEOUT, force_new=False, **settings):
    """Create a pyelasticsearch `ElasticSearch` object and return it.

    This will aggressively re-use `ElasticSearch` objects with the
    following rules:

    1. if you pass the same argument values to `get_es()`, then it
       will return the same `ElasticSearch` object
    2. if you pass different argument values to `get_es()`, then it
       will return different `ElasticSearch` object
    3. it caches each `ElasticSearch` object that gets created
    4. if you pass in `force_new=True`, then you are guaranteed to get
       a fresh `ElasticSearch` object AND that object will not be
       cached

    :arg urls: list of uris; ElasticSearch hosts to connect to,
        defaults to ``['http://localhost:9200']``
    :arg timeout: int; the timeout in seconds, defaults to 5
    :arg force_new: Forces get_es() to generate a new ElasticSearch
        object rather than pulling it from cache.
    :arg settings: other settings to pass into ElasticSearch
        constructor See
        `<http://pyelasticsearch.readthedocs.org/en/latest/api/>`_ for
        more details.

    Examples::

        # Returns cached ElasticSearch object
        es = get_es()

        # Returns a new ElasticSearch object
        es = get_es(force_new=True)

        es = get_es(urls=['http://localhost:9200'])

        es = get_es(urls=['http://localhost:9200'], timeout=10,
                    max_retries=3)

    """
    # Cheap way of de-None-ifying things
    urls = urls or DEFAULT_URLS

    # v0.7: Check for 'hosts' instead of 'urls'. Take this out in v1.0.
    if 'hosts' in settings:
        raise DeprecationWarning('"hosts" is deprecated in favor of "urls".')

    if not force_new:
        key = _build_key(urls, timeout, **settings)
        if key in _cached_elasticsearch:
            return _cached_elasticsearch[key]

    es = ElasticSearch(urls, timeout=timeout, **settings)

    if not force_new:
        # We don't need to rebuild the key here since we built it in
        # the previous if block, so it's in the namespace. Having said
        # that, this is a little ew.
        _cached_elasticsearch[key] = es

    return es


def split_field_action(s):
    """Takes a string and splits it into field and action

    Example::

    >>> split_field_action('foo__bar')
    'foo', 'bar'
    >>> split_field_action('foo')
    'foo', None

    """
    if '__' in s:
        return s.rsplit('__', 1)
    return s, None


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

    Makes it easier to create filters cumulatively using ``&`` (and),
    ``|`` (or) and ``~`` (not) operations.

    For example::

        f = F()
        f &= F(price='Free')
        f |= F(style='Mexican')

    creates a filter "price = 'Free' or style = 'Mexican'".

    :property filters: a list of the filters in this F; filters are
        either a dict or (key, val) tuple

    """
    def __init__(self, **filters):
        """Creates an F

        :raises InvalidFieldActionError: if the field action is not
            valid

        """
        filters = filters.items()
        if len(filters) > 1:
            self.filters = [{'and': filters}]
        else:
            self.filters = filters

    def __repr__(self):
        return '<F {0}>'.format(self.filters)

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
        elif conn in self.filters[0]:
            f.filters = self_filters
            f.filters[0][conn].extend(other_filters)
        elif conn in other.filters[0]:
            f.filters = other_filters
            f.filters[0][conn].extend(self_filters)
        else:
            f.filters = [{conn: self_filters + other_filters}]

        return f

    def __or__(self, other):
        return self._combine(other, 'or')

    def __and__(self, other):
        return self._combine(other, 'and')

    def __invert__(self):
        f = F()
        self_filters = copy.deepcopy(self.filters)
        if len(self_filters) == 0:
            f.filters = []
        elif (len(self_filters) < 2
            and 'not' in self_filters
            and 'filter' in self_filters['not']):
            f.filters = self_filters['not']['filter']
        else:
            f.filters = [{'not': {'filter': self_filters}}]
        return f


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

    **Adding filter support**

    You can add support for filters that S doesn't have support for by
    subclassing S with a method called ``process_filter_ACTION``.
    This method takes a key, value and an action.

    For example::

        claass FunkyS(S):
            def process_filter_funkyfilter(self, key, val, action):
                return {'funkyfilter': {'field': key, 'value': val}}


    Then you can use that just like other actions::

        s = FunkyS().filter(F(foo__funkyfilter='bar'))
        s = FunkyS().filter(foo__funkyfilter='bar')

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
        try:
            return '<S {0}>'.format(repr(self._build_query()))
        except RuntimeError:
            # This happens when you're debugging _build_query and try
            # to repr the instance you're calling it on. Then that
            # calls _build_query and ...
            return repr(self.steps)

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
        """Return a new S with specified ElasticSearch settings.

        This allows you to configure the ElasticSearch that gets used
        to execute the search.

        :arg settings: the settings you'd use to build the
            ElasticSearch---same as what you'd pass to
            :py:func:`get_es`.

        """
        return self._clone(next_step=('es', settings))

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

            With no arguments, returns a list of tuples of all the
            data for that document.

            With arguments, returns a list of tuples where the fields
            in the tuple are in the order specified.

        For example:

        >>> list(S().values_list())
        [(1, 'fred', 40), (2, 'brian', 30), (3, 'james', 45)]
        >>> list(S().values_list('id', 'name'))
        [(1, 'fred'), (2, 'brian'), (3, 'james')]
        >>> list(S().values_list('name', 'id')
        [('fred', 1), ('brian', 2), ('james', 3)]

        .. Note::

           If you don't specify fields, the data comes back in an
           arbitrary order. It's probably best to specify fields or
           use ``values_dict``.

        """
        return self._clone(next_step=('values_list', fields))

    def values_dict(self, *fields):
        """
        Return a new S instance that returns DictSearchResults.

        :arg fields: the list of fields to have in the results.

            With no arguments, this returns a list of dicts with all
            the fields.

            With arguments, it returns a list of dicts with the
            specified fields.

        For example:

        >>> list(S().values_dict())
        [{'id': 1, 'name': 'fred', 'age': 40}, ...]
        >>> list(S().values_dict('id', 'name')
        [{'id': 1, 'name': 'fred'}, ...]

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
        existing set with AND.

        :arg filters: this will be instances of F
        :arg kw: this will be in the form of ``field__action=value``

        Examples::

        >>> s = S().filter(foo='bar')
        >>> s = S().filter(F(foo='bar'))
        >>> s = S().filter(foo='bar', bat='baz')
        >>> s = S().filter(foo='bar').filter(bat='baz')

        By default, everything is combined using AND. If you provide
        multiple filters in a single filter call, those are ANDed
        together. If you provide multiple filters in multiple filter
        calls, those are ANDed together.

        If you want something different, use the F class which supports
        ``&`` (and), ``|`` (or) and ``~`` (not) operators. Then call
        filter once with the resulting F instance.

        See the documentation on :py:class:`elasticutils.F` for more
        details on composing filters with F.

        See the documentation on :py:class:`elasticutils.S` for adding
        support for additional actions.

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
        # of before_match and after_match tags. ElasticSearch can highlight more
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
                filters.extend(self._process_filters(value))
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
            elif action in ('es', 'indexes', 'doctypes', 'boost'):
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

    def _process_filters(self, filters):
        """Takes a list of filters and returns ES JSON API

        :arg filters: list of F, (key, val) tuples, or dicts

        :returns: list of ES JSON API filters

        """
        rv = []
        for f in filters:
            if isinstance(f, F):
                if f.filters:
                    rv.extend(self._process_filters(f.filters))
                    continue

            elif isinstance(f, dict):
                key = f.keys()[0]
                val = f[key]
                key = key.strip('_')

                if key not in ('or', 'and', 'not', 'filter'):
                    raise InvalidFieldActionError(
                        '%s is not a valid connector' % f.keys()[0])

                if 'filter' in val:
                    filter_filters = self._process_filters(val['filter'])
                    if len(filter_filters) == 1:
                        filter_filters = filter_filters[0]
                    rv.append({key: {'filter': filter_filters}})
                else:
                    rv.append({key: self._process_filters(val)})

            else:
                key, val = f
                key, field_action = split_field_action(key)
                handler_name = 'process_filter_{0}'.format(field_action)

                if field_action and hasattr(self, handler_name):
                    rv.append(getattr(self, handler_name)(
                            key, val, field_action))

                elif key.strip('_') in ('or', 'and', 'not'):
                    connector = key.strip('_')
                    rv.append({connector: self._process_filters(val.items())})

                elif field_action is None:
                    if val is None:
                        rv.append({'missing': {
                                    'field': key, "null_value": True}})
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

    def _process_queries(self, value):
        rv = []
        value = dict(value)
        or_ = value.pop('or_', [])
        for key, val in value.items():
            field_name, field_action = split_field_action(key)

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
        """Returns the ElasticSearch object to use.

        :arg default_builder: The function that takes a bunch of
            arguments and generates a pyelasticsearch ElasticSearch
            object.

        .. Note::

           If you desire special behavior regarding building the
           ElasticSearch object for this S, subclass S and override
           this method.

        """
        # .es() calls are incremental, so we go through them all and
        # update bits that are specified.
        args = {}
        for action, value in self.steps:
            if action == 'es':
                args.update(**value)

        # TODO: store the ElasticSearch on the S if we've already
        # created one since we don't need to do it multiple times.
        return default_builder(**args)

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

        index = self.get_indexes()
        doc_type = self.get_doctypes()

        if doc_type and not index:
            raise BadSearch(
                'You must specify an index if you are specifying doctypes.')

        hits = es.search(qs,
                         index=self.get_indexes(),
                         doc_type=self.get_doctypes())

        log.debug('[%s] %s' % (hits['took'], qs))
        return hits

    def count(self):
        """
        Executes search and returns number of results as an integer.

        :returns: integer

        For example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> count = s.count()

        """
        if self._results_cache:
            return self._results_cache.count
        else:
            return self[:0].raw()['hits']['total']

    def __len__(self):
        """
        Executes search and returns the number of results you'd get.

        Executes search and returns number of results as an integer.

        :returns: integer

        For example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> count = len(s)
        >>> results = s().execute()
        >>> count = len(results)
        True

        .. Note::

           This is very different than calling ``.count()``. If you
           call ``.count()`` you get the total number of results
           that ElasticSearch thinks matches your search. If you call
           ``len(s)``, then you get the number of results you'd get
           if you executed the search. This factors in slices and
           default from and size values.

        """
        return len(self._do_search())

    def all(self):
        """
        Executes search and returns ALL search results.

        :returns: `SearchResults` instance

        For example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> all_results = s.all()

        .. Warning::

           This returns ALL search results. The way it does this is by
           calling ``.count()`` first to figure out how many to return,
           then by slicing by that size and returning a list of ALL
           search results.

           Don't use this if you've got 1000s of results!

        """
        count = self.count()
        return self[:count].execute()


    def execute(self):
        """
        Executes search and returns a `SearchResults` object.

        :returns: `SearchResults` instance

        For example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> results = s.execute()
        """
        return self._do_search()

    def __iter__(self):
        """
        Executes search and returns an iterator of results.

        :returns: iterator of results

        For example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> for obj in s.execute():
        ...     print obj['id']
        ...

        """
        return iter(self._do_search())

    def _raw_facets(self):
        return self._do_search().results.get('facets', {})

    def facet_counts(self):
        """
        Executes search and returns facet counts.

        Example:

        >>> s = S().query(name__prefix='Jimmy')
        >>> facet_counts = s.facet_counts()

        """
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

    For example:

    >>> mlt = MLT(2034, index='addons_index', doctype='addon')
    >>> num_related_documents = len(mlt)
    >>> num_related_documents = list(mlt)

    """
    def __init__(self, id_, s=None, mlt_fields=None, index=None,
                 doctype=None, es=None, **query_params):
        """
        When the MLT is evaluated, it generates a list of dict results.

        :arg id_: The id of the document we want to find more like.
        :arg s: An instance of an S. Allows you to pass in a query which
            will be used as the body of the more-like-this request.
        :arg mlt_fields: A list of fields to look at for more like this.
        :arg index: The index to use. Falls back to the first index
            listed in s.get_indexes().
        :arg doctype: The doctype to use. Falls back to the first
            doctype listed in s.get_doctypes().
        :arg es: `The ElasticSearch` object to use. If you don't
            provide one, then it will create one for you.
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

        # v0.7: Check for the deprecated 'fields' argument and raise
        # an error. Take this out for v1.0.
        if 'fields' in query_params:
            raise DeprecationWarning(
                '"fields" argument is deprecated for "mlt_fields"')

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
        self.mlt_fields = mlt_fields
        self.es = es
        self.query_params = query_params
        self._results_cache = None

    def __iter__(self):
        return iter(self._do_search())

    def __len__(self):
        return len(self._do_search())

    def get_es(self):
        """Returns an `ElasticSearch`.

        * If there's an s, then it returns that `ElasticSearch`.
        * If the es was provided in the constructor, then it returns
          that `ElasticSearch`.
        * Otherwise, it creates a new `ElasticSearch` and returns
          that.

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

        params = dict(self.query_params)
        mlt_fields = self.mlt_fields or params.pop('mlt_fields', [])

        body = self.s._build_query() if self.s else ''

        hits = es.more_like_this(self.index, self.doctype, self.id, mlt_fields,
                                 body, **params)

        log.debug(hits)

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
    """
    After executing a search, this is the class that manages the
    results.

    :property type: the mapping type of the S that created this
        SearchResults instance
    :property took: the amount of time the search took
    :property count: the total results
    :property results: the raw ElasticSearch search response
    :property fields: the list of fields specified by values_list
        or values_dict

    When you iterate over this object, it returns the individual
    search results in the shape you asked for (object, tuple, dict,
    etc) in the order returned by ElasticSearch.

    Example::

        s = S().query(bio__text='archaeologist')
        results = s.execute()

        # Shows how long the search took
        print results.took

        # Shows the raw ElasticSearch response
        print results.results

    """

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
    """
    SearchResults subclass that returns a results in the form of a
    dict.
    """
    def set_objects(self, hits):
        key = 'fields' if self.fields else '_source'
        self.objects = [decorate_with_metadata(DictResult(r[key]), r)
                        for r in hits]


class ListSearchResults(SearchResults):
    """
    SearchResults subclass that returns a results in the form of a
    tuple.
    """
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
    """Takes a results from ElasticSearch and returns fields."""
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
    # ElasticSearch id
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

    1. implement ``get_indexes``.
    2. implement ``get_mapping_type_name``.
    3. if this ties back to a model, implement ``get_model`` and
       possibly also ``get_object``.

    For example::

        class ContactType(MappingType):
            @classmethod
            def get_indexes(cls):
                return 'contacts_index'

            @classmethod
            def get_mapping_type_name(cls):
                return 'contact_type'

            @classmethod
            def get_model(cls):
                return ContactModel

            def get_object(self):
                return self.get_model().get(id=self._id)

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
        which triggers lazy-loading of the object this document is
        based on.

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
    def get_index(cls):
        """Returns the index to use for this mapping type.

        You can specify the index to use for this mapping type.  This
        affects ``S`` built with this type.

        By default, raises NotImplementedError.

        Override this to return the index this mapping type should
        be indexed and searched in.

        """
        raise NotImplementedError()

    @classmethod
    def get_mapping_type_name(cls):
        """Returns the mapping type name.

        You can specify the mapping type name (also sometimes called the
        document type) with this method.

        By default, raises NotImplementedError.

        Override this to return the mapping type name.

        """
        raise NotImplementedError()

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
