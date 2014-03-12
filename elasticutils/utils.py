from itertools import islice


from elasticsearch.serializer import JSONSerializer


def to_json(data):
    """Convert Python structure to JSON used by Elasticsearch

    This is a helper method that uses the elasticsearch-py
    JSONSerializer to serialize the structure. This is the serializer
    that elasticsearch-py uses to serialize data for Elasticsearch and
    handles dates.

    :arg data: Python structure (e.g. dict, list, ...)

    :returns: string

    Examples:

    >>> to_json({'query': {'match': {'message': 'test message'}}})
    '{"query": {"match": {"message": "test message"}}}'

    >>> from elasticutils import S
    >>> some_s = S().query(message__match='test message')
    >>> to_json(some_s.build_search())
    '{"query": {"match": {"message": "test message"}}}'

    """
    return JSONSerializer().dumps(data)


def chunked(iterable, n):

    """Returns chunks of n length of iterable

    If len(iterable) % n != 0, then the last chunk will have length
    less than n.

    Example:

    >>> chunked([1, 2, 3, 4, 5], 2)
    [(1, 2), (3, 4), (5,)]

    """
    iterable = iter(iterable)
    while 1:
        t = tuple(islice(iterable, n))
        if t:
            yield t
        else:
            return


def format_explanation(explanation, indent='  ', indent_level=0):
    """Return explanation in an easier to read format

    Easier to read for me, at least.

    """
    if not explanation:
        return ''

    # Note: This is probably a crap implementation, but it's an
    # interesting starting point for a better formatter.
    line = ('%s%s %2.4f' % ((indent * indent_level),
                            explanation['description'],
                            explanation['value']))

    if 'details' in explanation:
        details = '\n'.join(
            [format_explanation(subtree, indent, indent_level + 1)
             for subtree in explanation['details']])
        return line + '\n' + details

    return line
