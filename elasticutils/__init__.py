import copy
import logging
from datetime import datetime
from operator import itemgetter

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk_index

from elasticutils._version import __version__  # noqa


log = logging.getLogger('elasticutils')


# Note: Don't change these--they're not part of the API.
DEFAULT_URLS = ['http://localhost:9200']
DEFAULT_DOCTYPES = None
DEFAULT_INDEXES = None
DEFAULT_TIMEOUT = 5


#: Maps ElasticUtils field actions to their Elasticsearch query names.
QUERY_ACTION_MAP = {
    None: 'term',  # Default to term
    'in': 'in',
    'term': 'term',
    'terms': 'terms',
    'startswith': 'prefix',  # Backwards compatability
    'prefix': 'prefix',
    'text': 'text',
    'text_phrase': 'text_phrase',
    'match': 'match',  # ES 0.19.9 renamed text to match
    'match_phrase': 'match_phrase',
    'wildcard': 'wildcard',
    'fuzzy': 'fuzzy'}


#: List of text/match actions.
TEXTMATCH_ACTIONS = ['text', 'text_phrase', 'match', 'match_phrase']
#: List of range actions.
RANGE_ACTIONS = ['gt', 'gte', 'lt', 'lte']


class ElasticUtilsError(Exception):
    """Base class for ElasticUtils errors."""
    pass


class InvalidFieldActionError(ElasticUtilsError):
    """Raise this when the field action doesn't exist"""
    pass


class InvalidFlagsError(ElasticUtilsError):
    """Raise when multiple flags are passed into a query"""
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
    # Elasticsearch. We'll probably have to tweak this.
    settings = sorted(settings.items(), key=lambda item: item[0])
    settings = repr([(k, v) for k, v in settings])

    # elasticsearch allows urls to be a string, so we make sure to
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
    """Create an elasticsearch `Elasticsearch` object and return it.

    This will aggressively re-use `Elasticsearch` objects with the
    following rules:

    1. if you pass the same argument values to `get_es()`, then it
       will return the same `Elasticsearch` object
    2. if you pass different argument values to `get_es()`, then it
       will return different `Elasticsearch` object
    3. it caches each `Elasticsearch` object that gets created
    4. if you pass in `force_new=True`, then you are guaranteed to get
       a fresh `Elasticsearch` object AND that object will not be
       cached

    :arg urls: list of uris; Elasticsearch hosts to connect to,
        defaults to ``['http://localhost:9200']``
    :arg timeout: int; the timeout in seconds, defaults to 5
    :arg force_new: Forces get_es() to generate a new Elasticsearch
        object rather than pulling it from cache.
    :arg settings: other settings to pass into Elasticsearch
        constructor; See
        `<http://elasticsearch.readthedocs.org/>`_ for more details.

    Examples::

        # Returns cached Elasticsearch object
        es = get_es()

        # Returns a new Elasticsearch object
        es = get_es(force_new=True)

        es = get_es(urls=['localhost:9200'])

        es = get_es(urls=['localhost:9200'], timeout=10,
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

    es = Elasticsearch(urls, timeout=timeout, **settings)

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

    """
    def __init__(self, **filters):
        """Creates an F"""
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
        elif (len(self_filters) == 1
              and isinstance(self_filters[0], dict)
              and self_filters[0].get('not', {}).get('filter', {})):
            f.filters = self_filters[0]['not']['filter']
        else:
            f.filters = [{'not': {'filter': self_filters}}]
        return f


class Q(object):
    """
    Query objects.

    Makes it easier to create queries cumulatively.

    If there's more than one query part, they're combined under a
    BooleanQuery. By default, they're combined in the `must` clause.

    You can combine two Q classes using the ``+`` operator. For
    example::

        q = Q()
        q += Q(title__text='shoes')
        q += Q(summary__text='shoes')

    creates a BooleanQuery with two `must` clauses.

    Example 2::

        q = Q()
        q += Q(title__text='shoes', should=True)
        q += Q(summary__text='shoes')
        q += Q(description__text='shoes', must=True)

    creates a BooleanQuery with one `should` clause (title) and two
    `must` clauses (summary and description).

    """
    def __init__(self, **queries):
        """Creates a Q"""
        self.should_q = []
        self.must_q = []
        self.must_not_q = []

        should_flag = queries.pop('should', False)
        must_flag = queries.pop('must', False)
        must_not_flag = queries.pop('must_not', False)

        # This (ab)uses the fact that booleans are integers.
        if should_flag + must_flag + must_not_flag > 1:
            raise InvalidFlagsError(
                'Either should, must or must_not can be True, but not '
                'more than one.')

        if should_flag:
            self.should_q.extend(queries.items())
        elif must_not_flag:
            self.must_not_q.extend(queries.items())
        else:
            self.must_q.extend(queries.items())

    def __repr__(self):
        return '<Q should={0} must={1} must_not={2}>'.format(
            self.should_q, self.must_q, self.must_not_q)

    def __add__(self, other):
        q = Q()

        # Note: LHS takes precedence over RHS
        q.should_q = list(self.should_q)
        q.must_q = list(self.must_q)
        q.must_not_q = list(self.must_not_q)

        q.should_q.extend(other.should_q)
        q.must_q.extend(other.must_q)
        q.must_not_q.extend(other.must_not_q)
        return q

    def __eq__(self, other):
        return (sorted(self.should_q) == sorted(other.should_q)
                and sorted(self.must_q) == sorted(other.must_q)
                and sorted(self.must_not_q) == sorted(other.must_not_q))


def _boosted_value(name, action, key, value, boost):
    """Boost a value if we should in _process_queries"""
    if boost is not None:
        # Note: Most queries use 'value' for the key name except
        # Text/Match queries which use 'query'. So we have to do some
        # switcheroo for that.
        value_key = 'query' if action in TEXTMATCH_ACTIONS else 'value'
        return {name: {'boost': boost, value_key: value}}
    return {name: value}


class PythonMixin(object):
    """Mixin that provides ES results fixing"""
    def to_python(self, obj):
        """Converts strings in a data structure to Python types

        It converts datetime-ish things to Python datetimes.

        Override if you want something different.

        :arg obj: Python datastructure

        :returns: Python datastructure with strings converted to
            Python types

        .. Note::

           This does the conversion in-place!

        """
        if isinstance(obj, basestring):
            if len(obj) == 19:
                try:
                    return datetime.strptime(obj, '%Y-%m-%dT%H:%M:%S')
                except (TypeError, ValueError):
                    pass
            elif len(obj) == 10:
                try:
                    return datetime.strptime(obj, '%Y-%m-%d')
                except (TypeError, ValueError):
                    pass

        elif isinstance(obj, dict):
            for key, val in obj.items():
                obj[key] = self.to_python(val)

        elif isinstance(obj, list):
            return [self.to_python(item) for item in obj]

        return obj


class S(PythonMixin):
    """Represents a lazy Elasticsearch Search API request.

    The API for `S` takes inspiration from Django's QuerySet.

    `S` can be either typed or untyped. An untyped `S` returns dict
    results by default.

    An `S` is lazy in the sense that it doesn't do an Elasticsearch
    search request until it's forced to evaluate by either iterating
    over it, calling ``.count``, doing ``len(s)``, or calling
    ``.facet_count``.


    **Adding support for other queries**

    You can add support for queries that S doesn't have support for by
    subclassing S with a method called ``process_query_ACTION``.  This
    method takes a key, value and an action.

    For example::

        claass FunkyS(S):
            def process_query_funkyquery(self, key, val, action):
                return {'funkyquery': {'field': key, 'value': val}}


    Then you can use that just like other actions::

        s = FunkyS().query(Q(foo__funkyquery='bar'))
        s = FunkyS().query(foo__funkyquery='bar')


    Many Elasticsearch queries take other arguments. This is a good
    way of using different arguments. For example, if you wanted
    to write a handler for fuzzy for dates, you could do::

        claass FunkyS(S):
            def process_query_fuzzy(self, key, val, action):
                # val here is a (value, min_similarity) tuple
                return {
                    'funkyquery': {
                        key: {
                            'value': val[0],
                            'min_similarity': val[1]
                        }
                    }
                }

    Used::

        s = FunkyS().query(created__fuzzy=(created_dte, '1d'))


    **Adding support for other filters**

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
        """Return a new S with specified Elasticsearch settings.

        This allows you to configure the Elasticsearch object that gets
        used to execute the search.

        :arg settings: the settings you'd use to build the
            Elasticsearch---same as what you'd pass to
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

           Elasticsearch calls these "mapping types". It's the name
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
        >>> list(S().values_list('name', 'id'))
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
        >>> list(S().values_dict('id', 'name'))
        [{'id': 1, 'name': 'fred'}, ...]

        """
        return self._clone(next_step=('values_dict', fields))

    def order_by(self, *fields):
        """
        Return a new S instance with results ordered as specified

        You can change the order search results by specified fields::

            q = (S().query(title='trucks')
                    .order_by('title')


        This orders search results by the `title` field in ascending
        order.

        If you want to sort by descending order, prepend a ``-``::

            q = (S().query(title='trucks')
                    .order_by('-title')


        You can also sort by the computed field ``_score``.

        .. Note::

           Calling this again will overwrite previous ``.order_by()``
           calls.

        """
        return self._clone(next_step=('order_by', fields))

    def query(self, *queries, **kw):
        """
        Return a new S instance with query args combined with existing
        set in a must boolean query.

        :arg queries: instances of Q
        :arg kw: queries in the form of ``field__action=value``

        There are three special flags you can use:

        * ``must=True``: Specifies that the queries and kw queries
          **must match** in order for a document to be in the result.

          If you don't specify a special flag, this is the default.

        * ``should=True``: Specifies that the queries and kw queries
          **should match** in order for a document to be in the result.

        * ``must_not=True``: Specifies the queries and kw queries
          **must not match** in order for a document to be in the result.

        These flags work by putting those queries in the appropriate
        clause of an Elasticsearch boolean query.

        Examples:

        >>> s = S().query(foo='bar')
        >>> s = S().query(Q(foo='bar'))
        >>> s = S().query(foo='bar', bat__text='baz')
        >>> s = S().query(foo='bar', should=True)
        >>> s = S().query(foo='bar', should=True).query(baz='bat', must=True)

        Notes:

        1. Don't specify multiple special flags, but if you did, `should`
           takes precedence.
        2. If you don't specify any, it defaults to `must`.
        3. You can specify special flags in the
           :py:class:`elasticutils.Q`, too. If you're building your
           query incrementally, using :py:class:`elasticutils.Q` helps
           a lot.

        See the documentation on :py:class:`elasticutils.Q` for more
        details on composing queries with Q.

        See the documentation on :py:class:`elasticutils.S` for more
        details on adding support for more query types.

        """
        q = Q()
        for query in queries:
            q += query

        if 'or_' in kw:
            # Backwards compatibile with pre-0.7 version.
            or_query = kw.pop('or_')

            # or_query here is a dict of key/val pairs. or_ indicates
            # they're in a should clause, so we generate the
            # equivalent Q and then add it in.
            or_query['should'] = True
            q += Q(**or_query)

        q += Q(**kw)

        return self._clone(next_step=('query', q))

    def query_raw(self, query):
        """
        Return a new S instance with a query_raw.

        :arg query: Python dict specifying the complete query to send
            to Elasticsearch

        Example::

            S().query_raw({'match': {'title': 'example'}})


        .. Note::

           If there's a query_raw in your S, then that's your
           query. All ``.query()``, ``.demote()``, ``.boost()`` and
           anything else that affects the query clause is ignored.

        """
        return self._clone(next_step=('query_raw', query))

    def filter(self, *filters, **kw):
        """
        Return a new S instance with filter args combined with
        existing set with AND.

        :arg filters: this will be instances of F
        :arg kw: this will be in the form of ``field__action=value``

        Examples:

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

        See the documentation on :py:class:`elasticutils.S` for more
        details on adding support for new filter types.

        """
        return self._clone(next_step=('filter', list(filters) + kw.items()))

    def filter_raw(self, filter_):
        """
        Return a new S instance with a filter_raw.

        :arg filter_: Python dict specifying the complete filter to send
            to Elasticsearch

        Example::

            S().filter_raw({'term': {'title': 'example'}})


        .. Note::

           If there's a filter_raw in your S, then that's your
           filter. All ``.filter()`` and anything else that affects the
           filter clause is ignored.
        """
        return self._clone(next_step=('filter_raw', filter_))

    def boost(self, **kw):
        """
        Return a new S instance with field boosts.

        ElasticUtils allows you to specify query-time field boosts
        with ``.boost()``. It takes a set of arguments where the keys
        are either field names or field name + ``__`` + field action.

        Examples::

            q = (S().query(title='taco trucks',
                           description__text='awesome')
                    .boost(title=4.0, description__text=2.0))


        If the key is a field name, then the boost will apply to all
        query bits that have that field name. For example::

            q = (S().query(title='trucks',
                           title__prefix='trucks',
                           title__fuzzy='trucks')
                    .boost(title=4.0))


        applies a 4.0 boost to all three query bits because all three
        query bits are for the title field name.

        If the key is a field name and field action, then the boost
        will apply only to that field name and field action. For
        example::

            q = (S().query(title='trucks',
                           title__prefix='trucks',
                           title__fuzzy='trucks')
                    .boost(title__prefix=4.0))


        will only apply the 4.0 boost to title__prefix.

        Boosts are relative to one another and all boosts default to
        1.0.

        For example, if you had::

            qs = (S().boost(title=4.0, summary=2.0)
                     .query(title__text=value,
                            summary__text=value,
                            content__text=value,
                            should=True))


        ``title__text`` would be boosted twice as much as
        ``summary__text`` and ``summary__text`` twice as much as
        ``content__text``.

        """
        new = self._clone()
        new.field_boosts.update(kw)
        return new

    def demote(self, amount_, *queries, **kw):
        """
        Returns a new S instance with boosting query and demotion.

        You can demote documents that match query criteria::

            q = (S().query(title='trucks')
                    .demote(0.5, description__text='gross'))

            q = (S().query(title='trucks')
                    .demote(0.5, Q(description__text='gross')))

        This is implemented using the boosting query in
        Elasticsearch. Anything you specify with ``.query()`` goes
        into the positive section. The negative query and negative
        boost portions are specified as the first and second arguments
        to ``.demote()``.

        .. Note::

           Calling this again will overwrite previous ``.demote()``
           calls.

        """
        q = Q()
        for query in queries:
            q += query
        q += Q(**kw)

        return self._clone(next_step=('demote', (amount_, q)))

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

        :arg fields: The list of fields to highlight. If the field is
            None, then the highlight is cleared.

        Additional keyword options:

        * ``pre_tags`` -- List of tags before highlighted portion
        * ``post_tags`` -- List of tags after highlighted portion

        Results will have a ``_highlight`` property which contains
        the highlighted field excerpts.

        For example::

            q = (S().query(title__text='crash', content__text='crash')
                    .highlight('title', 'content'))

            for result in q:
                print result._highlight['title']
                print result._highlight['content']


        If you pass in ``None``, it will clear the highlight.

        For example, this search won't highlight anything::

            q = (S().query(title__text='crash')
                    .highlight('title')          # highlights 'title' field
                    .highlight(None))            # clears highlight


        .. Note::

           Calling this again will overwrite previous ``.highlight()``
           calls.

        .. Note::

           Make sure the fields you're highlighting are indexed
           correctly.  Read the Elasticsearch documentation for
           details.

        """
        return self._clone(next_step=('highlight', (fields, kwargs)))

    def extra(self, **kw):
        """
        Return a new S instance with extra args combined with existing
        set.
        """
        new = self._clone()
        actions = ['values_list', 'values_dict', 'order_by', 'query',
                   'filter', 'facet']
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
        Elasticsearch, and return it as a dict.
        """
        filters = []
        filters_raw = None
        queries = []
        query_raw = None
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
                queries.append(value)
            elif action == 'query_raw':
                query_raw = value
            elif action == 'demote':
                # value here is a tuple of (negative_boost, query)
                demote = value
            elif action == 'filter':
                filters.extend(self._process_filters(value))
            elif action == 'filter_raw':
                filters_raw = value
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

        # If there's a filters_raw, we use that.
        if filters_raw:
            qs['filter'] = filters_raw
        else:
            if len(filters) > 1:
                qs['filter'] = {'and': filters}
            elif filters:
                qs['filter'] = filters[0]

        # If there's a query_raw, we use that. Otherwise we use
        # whatever we got from query and demote.
        if query_raw:
            qs['query'] = query_raw

        else:
            pq = self._process_queries(queries)

            if demote is not None:
                qs['query'] = {
                    'boosting': {
                        'negative': self._process_queries([demote[1]]),
                        'negative_boost': demote[0]
                        }
                    }
                if pq:
                    qs['query']['boosting']['positive'] = pq

            elif pq:
                qs['query'] = pq

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

                elif field_action in RANGE_ACTIONS:
                    rv.append({'range': {key: {field_action: val}}})

                elif field_action == 'range':
                    lower, upper = val
                    rv.append({'range': {key: {'gte': lower, 'lte': upper}}})

                else:
                    raise InvalidFieldActionError(
                        '%s is not a valid field action' % field_action)

        return rv

    def _process_query(self, query):
        """Takes a key/val pair and returns ES JSON API"""
        key, val = query
        field_name, field_action = split_field_action(key)

        # Boost by name__action overrides boost by name.
        boost = self.field_boosts.get(key)
        if boost is None:
            boost = self.field_boosts.get(field_name)

        handler_name = 'process_query_{0}'.format(field_action)

        if field_action and hasattr(self, handler_name):
            return getattr(self, handler_name)(field_name, val, field_action)

        elif field_action in QUERY_ACTION_MAP:
            return {
                QUERY_ACTION_MAP[field_action]: _boosted_value(
                    field_name, field_action, key, val, boost)
            }

        elif field_action == 'query_string':
            # query_string has different syntax, so it's handled
            # differently.
            #
            # Note: query_string queries are not boosted with
            # .boost()---they're boosted in the query text itself.
            return {
                'query_string': {'default_field': field_name, 'query': val}
            }

        elif field_action in RANGE_ACTIONS:
            # Ranges are special and have a different syntax, so
            # we handle them separately.
            return {
                'range': {field_name: _boosted_value(
                        field_action, field_action, key, val, boost)}
           }

        elif field_action == 'range':
            lower, upper = val
            value = {
                'gte': lower,
                'lte': upper,
            }
            if boost:
                value['boost'] = boost

            return {'range': {field_name: value}}

        raise InvalidFieldActionError(
            '%s is not a valid field action' % field_action)

    def _process_queries(self, queries):
        """Takes a list of queries and returns query clause value

        :arg queries: list of Q instances

        :returns: dict which is the query clause value

        """
        # First, let's mush everything into a single Q. Then we can
        # parse that into bits.
        new_q = Q()

        for query in queries:
            new_q += query

        # Now we have a single Q that needs to be processed.
        should_q = [self._process_query(query) for query in new_q.should_q]
        must_q = [self._process_query(query) for query in new_q.must_q]
        must_not_q = [self._process_query(query) for query in new_q.must_not_q]

        if len(must_q) > 1 or (len(should_q) + len(must_not_q) > 0):
            # If there's more than one must_q or there are must_not_q
            # or should_q, then we need to wrap the whole thing in a
            # boolean query.
            bool_query = {}
            if must_q:
                bool_query['must'] = must_q
            if should_q:
                bool_query['should'] = should_q
            if must_not_q:
                bool_query['must_not'] = must_not_q
            return {'bool': bool_query}

        if must_q:
            # There's only one must_q query and that's it, so we hoist
            # that.
            return must_q[0]

        return {}

    def get_results_class(self):
        """Returns the results class to use

        The results class should be a subclass of SearchResults.

        """
        if self.as_list:
            return ListSearchResults
        elif self.as_dict:
            return DictSearchResults
        else:
            return ObjectSearchResults

    def _do_search(self):
        """
        Perform the search, then convert that raw format into a
        SearchResults instance and return it.
        """
        if self._results_cache is None:
            response = self.raw()
            ResultsClass = self.get_results_class()
            results = self.to_python(response.get('hits', {}).get('hits', []))
            self._results_cache = ResultsClass(
                self.type, response, results, self.fields)
        return self._results_cache

    def get_es(self, default_builder=get_es):
        """Returns the Elasticsearch object to use.

        :arg default_builder: The function that takes a bunch of
            arguments and generates a elasticsearch Elasticsearch
            object.

        .. Note::

           If you desire special behavior regarding building the
           Elasticsearch object for this S, subclass S and override
           this method.

        """
        # .es() calls are incremental, so we go through them all and
        # update bits that are specified.
        args = {}
        for action, value in self.steps:
            if action == 'es':
                args.update(**value)

        # TODO: store the Elasticsearch on the S if we've already
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
        Build query and passes to Elasticsearch, then returns the raw
        format returned.
        """
        qs = self._build_query()
        es = self.get_es()

        index = self.get_indexes()
        doc_type = self.get_doctypes()

        if doc_type and not index:
            raise BadSearch(
                'You must specify an index if you are specifying doctypes.')

        hits = es.search(body=qs,
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
           that Elasticsearch thinks matches your search. If you call
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
        return self._do_search().response.get('facets', {})

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
            elif val['_type'] == 'histogram':
                facets[key] = [v for v in val['entries']]
            elif val['_type'] == 'date_histogram':
                facets[key] = [v for v in val['entries']]
            elif val['_type'] in ('filter', 'query', 'statistical'):
                facets[key] = val
            else:
                raise InvalidFacetType(
                    'Facet _type "%s". key "%s" val "%r"' %
                    (val['_type'], key, val))
        return facets


class MLT(PythonMixin):
    """Represents a lazy Elasticsearch More Like This API request.

    This is lazy in the sense that it doesn't evaluate and execute the
    Elasticsearch request unless you force it to by iterating over it
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
        :arg es: The `Elasticsearch` object to use. If you don't
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
        """Returns an `Elasticsearch`.

        * If there's an s, then it returns that `Elasticsearch`.
        * If the es was provided in the constructor, then it returns
          that `Elasticsearch`.
        * Otherwise, it creates a new `Elasticsearch` and returns
          that.

        Override this if that behavior isn't correct for you.

        """
        if self.s:
            return self.s.get_es()

        return self.es or get_es()

    def raw(self):
        """
        Build query and passes to `Elasticsearch`, then returns the raw
        format returned.
        """
        es = self.get_es()

        params = dict(self.query_params)
        mlt_fields = self.mlt_fields or params.pop('mlt_fields', [])

        body = self.s._build_query() if self.s else ''

        hits = es.mlt(
            index=self.index, doc_type=self.doctype, id=self.id,
            mlt_fields=mlt_fields, body=body, **params)

        log.debug(hits)

        return hits

    def _do_search(self):
        """
        Perform the mlt call, then convert that raw format into a
        SearchResults instance and return it.
        """
        if self._results_cache is None:
            response = self.raw()
            results = self.to_python(response.get('hits', {}).get('hits', []))
            self._results_cache = DictSearchResults(
                self.type, response, results, None)
        return self._results_cache


class SearchResults(object):
    """
    After executing a search, this is the class that manages the
    results.

    :property type: the mapping type of the S that created this
        SearchResults instance
    :property took: the amount of time the search took
    :property count: the total results
    :property response: the raw Elasticsearch search response
    :property results: the search results from the response if any
    :property fields: the list of fields specified by values_list
        or values_dict

    When you iterate over this object, it returns the individual
    search results in the shape you asked for (object, tuple, dict,
    etc) in the order returned by Elasticsearch.

    Example::

        s = S().query(bio__text='archaeologist')
        results = s.execute()

        # Shows how long the search took
        print results.took

        # Shows the raw Elasticsearch response
        print results.results

    """

    def __init__(self, type, response, results, fields):
        self.type = type
        self.response = response
        self.took = response.get('took', 0)
        self.count = response.get('hits', {}).get('total', 0)
        self.results = results
        self.fields = fields

        self.set_objects(self.results)

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
    def set_objects(self, results):
        key = 'fields' if self.fields else '_source'
        self.objects = [decorate_with_metadata(DictResult(r[key]), r)
                        for r in results]


class ListSearchResults(SearchResults):
    """
    SearchResults subclass that returns a results in the form of a
    tuple.
    """
    def set_objects(self, results):
        if self.fields:
            getter = itemgetter(*self.fields)
            objs = [(getter(r['fields']), r) for r in results]

            # itemgetter returns an item--not a tuple of one item--if
            # there is only one thing in self.fields. Since we want
            # this to always return a list of tuples, we need to fix
            # that case here.
            if len(self.fields) == 1:
                objs = [((obj,), r) for obj, r in objs]
        else:
            objs = [(r['_source'].values(), r) for r in results]
        self.objects = [decorate_with_metadata(TupleResult(obj), r)
                        for obj, r in objs]


def _convert_results_to_dict(r):
    """Takes a results from Elasticsearch and returns fields."""
    if 'fields' in r:
        return r['fields']
    if '_source' in r:
        return r['_source']
    return {'id': r['_id']}


class ObjectSearchResults(SearchResults):
    def set_objects(self, results):
        mapping_type = (self.type if self.type is not None
                        else DefaultMappingType)
        self.objects = [
            decorate_with_metadata(
                mapping_type.from_results(_convert_results_to_dict(r)),
                r)
            for r in results]

    def __iter__(self):
        return self.objects.__iter__()


def decorate_with_metadata(obj, result):
    """Return obj decorated with result-scope metadata."""
    # Elasticsearch id
    obj._id = result.get('_id', 0)
    # Source data
    obj._source = result.get('_source', {})
    # The search result score
    obj._score = result.get('_score')
    # The document type
    obj._type = result.get('_type')
    # Explanation structure
    obj._explanation = result.get('_explanation', {})
    # Highlight bits
    obj._highlight = result.get('highlight', {})
    return obj


class NoModelError(Exception):
    pass


class MappingType(object):
    """Base class for mapping types.

    To extend this class:

    1. implement ``get_index``.
    2. implement ``get_mapping_type_name``.
    3. if this ties back to a model, implement ``get_model`` and
       possibly also ``get_object``.

    For example::

        class ContactType(MappingType):
            @classmethod
            def get_index(cls):
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

    def get_object(self):
        """Returns the model instance

        This gets called when someone uses the ``.object`` attribute
        which triggers lazy-loading of the object this document is
        based on.

        By default, this calls::

            self.get_model().get(id=self._id)


        where ``self._id`` is the Elasticsearch document id.

        Override it to do something different.

        """
        return self.get_model().get(id=self._id)

    @classmethod
    def get_model(cls):
        """Return the model class related to this MappingType.

        This can be any class that has an instance related to this
        Mappingtype by id.

        By default, raises NoModelError.

        Override this to return a class that works with
        ``.get_object()`` to return the instance of the model that is
        related to this document.

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


class Indexable(object):
    """Mixin for mapping types with all the indexing hoo-hah.

    Add this mixin to your DjangoMappingType subclass and it gives you
    super indexing power.

    """

    @classmethod
    def get_es(cls):
        """Returns an Elasticsearch object

        Override this if you need special functionality.

        :returns: a elasticsearch `Elasticsearch` instance

        """
        return get_es()

    @classmethod
    def get_mapping(cls):
        """Returns the mapping for this mapping type.

        Example::

            @classmethod
            def get_mapping(cls):
                return {
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'}
                    }
                }


        See the docs for more details on how to specify a mapping.

        Override this to return a mapping for this doctype.

        :returns: dict representing the Elasticsearch mapping or None
            if you want Elasticsearch to infer it. defaults to None.

        """
        return None

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        """Extracts the Elasticsearch index document for this instance

        **This must be implemented.**

        .. Note::

           The resulting dict must be JSON serializable.

        :arg obj_id: the object id for the object to extract from
        :arg obj: if this is not None, use this as the object to
            extract from; this allows you to fetch a bunch of items
            at once and extract them one at a time

        :returns: dict of key/value pairs representing the document

        """
        raise NotImplementedError

    @classmethod
    def get_indexable(cls):
        """Returns an iterable of things to index.

        :returns: iterable of things to index

        """
        raise NotImplemented

    @classmethod
    def index(cls, document, id_=None, overwrite_existing=True, es=None,
              index=None):
        """Adds or updates a document to the index

        :arg document: Python dict of key/value pairs representing
            the document

            .. Note::

               This must be serializable into JSON.

        :arg id_: the id of the document

            .. Note::

               If you don't provide an ``id_``, then Elasticsearch
               will make up an id for your document and it'll look
               like a character name from a Lovecraft novel.

        :arg overwrite_existing: if ``True`` overwrites existing documents
             of the same ID and doctype

        :arg es: The `Elasticsearch` to use. If you don't specify an
            `Elasticsearch`, it'll use `cls.get_es()`.

        :arg index: The name of the index to use. If you don't specify one
            it'll use `cls.get_index()`.

        .. Note::

           If you need the documents available for searches
           immediately, make sure to refresh the index by calling
           ``refresh_index()``.

        """
        if es is None:
            es = cls.get_es()

        if index is None:
            index = cls.get_index()

        kw = {}
        if overwrite_existing:
            kw['op_type'] = 'create'
        es.index(
            index,
            cls.get_mapping_type_name(),
            document,
            id=id_,
            **kw)

    @classmethod
    def bulk_index(cls, documents, id_field='id', es=None, index=None):
        """Adds or updates a batch of documents.

        :arg documents: List of Python dicts representing individual
            documents to be added to the index

            .. Note::

               This must be serializable into JSON.

        :arg id_field: The name of the field to use as the document
            id. This defaults to 'id'.

        :arg es: The `Elasticsearch` to use. If you don't specify an
            `Elasticsearch`, it'll use `cls.get_es()`.

        :arg index: The name of the index to use. If you don't specify one
            it'll use `cls.get_index()`.

        .. Note::

           If you need the documents available for searches
           immediately, make sure to refresh the index by calling
           ``refresh_index()``.

        """
        if es is None:
            es = cls.get_es()

        if index is None:
            index = cls.get_index()

        documents = (dict(d, _id=d[id_field]) for d in documents)

        bulk_index(es, documents, 
                      index=index,
                      doc_type=cls.get_mapping_type_name())

    @classmethod
    def unindex(cls, id_, es=None, index=None):
        """Removes a particular item from the search index.

        :arg id_: The Elasticsearch id for the document to remove from
            the index.

        :arg es: The `Elasticsearch` to use. If you don't specify an
            `Elasticsearch`, it'll use `cls.get_es()`.

        :arg index: The name of the index to use. If you don't specify one
            it'll use `cls.get_index()`.

        """
        if es is None:
            es = cls.get_es()

        if index is None:
            index = cls.get_index()

        es.delete(index, cls.get_mapping_type_name(), id_)

    @classmethod
    def refresh_index(cls, es=None, index=None):
        """Refreshes the index.

        Elasticsearch will update the index periodically
        automatically. If you need to see the documents you just
        indexed in your search results right now, you should call
        `refresh_index` as soon as you're done indexing. This is
        particularly helpful for unit tests.

        :arg es: The `Elasticsearch` to use. If you don't specify an
            `Elasticsearch`, it'll use `cls.get_es()`.

        :arg index: The name of the index to use. If you don't specify one
            it'll use `cls.get_index()`.

        """
        if es is None:
            es = cls.get_es()

        if index is None:
            index = cls.get_index()

        es.indices.refresh(index)
