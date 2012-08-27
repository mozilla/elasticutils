from django.conf import settings

from elasticutils.contrib.django import get_es, S


class SearchMixin(object):
    """Mixin for indexing Django model instances

    Add this mixin to your Django ORM model class and it gives you
    super indexing power. This correlates an ES mapping type to a
    Django ORM model. Using this allows you to get Django model
    instances as ES search results.

    """

    @classmethod
    def get_index(cls):
        """Gets the index for this model.

        The index for this model is specified in `settings.ES_INDEXES`
        which is a dict of mapping type -> index name.

        By default, this uses `.get_mapping_type()` to determine the
        mapping and returns the value in `settings.ES_INDEXES` for that
        or ``settings.ES_INDEXES['default']``.

        Override this to compute it differently.

        :returns: index name to use

        """
        indexes = settings.ES_INDEXES
        return indexes.get(cls.get_mapping_type()) or indexes['default']

    @classmethod
    def get_mapping_type(cls):
        """Returns the name of the mapping.

        By default, this is ``cls._meta.db_table``.

        Override this if you want to compute the mapping type name
        differently.

        :returns: mapping type string

        """
        return cls._meta.db_table

    @classmethod
    def get_mapping(cls):
        """Returns the mapping for this mapping type.

        See the docs for details on how to specify a mapping.

        Override this to return a mapping for this doctype.

        :returns: dict representing the ES mapping or None if you
            want ES to infer it. defaults to None.

        """
        return None

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        """Extracts the ES index document for this instance

        This must be implemented.

        .. Note::

           The resulting dict must be JSON serializable.

        :arg obj_id: the object id for the instance to extract from
        :arg obj: if this is not None, use this as the object to
            extract from; this allows you to fetch a bunch of items
            at once and extract them one at a time

        :returns: dict of key/value pairs representing the document

        """
        raise NotImplementedError

    @classmethod
    def get_indexable(cls):
        """Returns the queryset of ids of all things to be indexed.

        Defaults to::

            cls.objects.order_by('id').values_list('id', flat=True)

        :returns: iterable of ids of objects to be indexed

        """
        return cls.objects.order_by('id').values_list('id', flat=True)

    @classmethod
    def index(cls, document, id_=None, bulk=False, force_insert=False,
              es=None):
        """Adds or updates a document to the index

        :arg document: Python dict of key/value pairs representing
            the document

            .. Note::

               This must be serializable into JSON.

        :arg id_: the Django ORM model instance id---this is used to
            convert an ES search result back to the Django ORM model
            instance from the db. It should be an integer.
        :arg bulk: Whether or not this is part of a bulk indexing.  If
            this is, you must provide an ES with the `es` argument,
            too.
        :arg force_insert: TODO
        :arg es: The ES to use. If you don't specify an ES, it'll
            use `elasticutils.contrib.django.get_es()`.

        :raises ValueError: if `bulk` is True, but `es` is None.

        TODO: add example.

        """
        if bulk and es is None:
            raise ValueError('bulk is True, but es is None')

        if es is None:
            es = get_es()

        es.index(
            document, index=cls.get_index(), doc_type=cls.get_mapping_type(),
            id=id_, bulk=bulk, force_insert=force_insert)

    @classmethod
    def unindex(cls, id, es=None):
        """Removes a particular item from the search index.

        TODO: document this better.

        """
        if es is None:
            es = get_es()

        es.delete(cls.get_index(), cls.get_mapping_type(), id)

    @classmethod
    def refresh_index(cls, timesleep=0, es=None):
        """Refreshes the index.

        TODO: document this better.

        """
        if es is None:
            es = get_es()

        es.refresh(cls.get_index(), timesleep=timesleep)

    @classmethod
    def search(cls):
        """Returns a typed S for this class."""
        return S(cls).indexes(cls.get_index()).doctypes(cls.get_mapping_type())
