from django.conf import settings

from elasticutils import MappingType, NoModelError
from elasticutils.contrib.django import get_es, S


class DjangoMappingType(MappingType):
    """This has most of the pieces you need to tie back to a Django ORM model.

    Subclass this and override at least `get_model`.

    """
    def get_object(self):
        return self.get_model().get(pk=self._id)

    @classmethod
    def get_model(cls):
        """Return the model related to this DjangoMappingType.

        This can be any class that has an instance related to this
        DjangoMappingtype by id.

        Override this to return a model class.

        :returns: model class

        """
        raise NoModelError

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
        index = indexes.get(cls.get_mapping_type_name()) or indexes['default']
        if not (isinstance(index, basestring)):
            # FIXME - not sure what to do here, but we only want one
            # index and somehow this isn't one index.
            index = index[0]
        return index

    @classmethod
    def get_mapping_type_name(cls):
        """Returns the name of the mapping.

        By default, this is ``cls.get_model()._meta.db_table``.

        Override this if you want to compute the mapping type name
        differently.

        :returns: mapping type string

        """
        return cls.get_model()._meta.db_table

    @classmethod
    def search(cls):
        """Returns a typed S for this class.

        :returns: an `S`

        """
        return S(cls)


class Indexable(object):
    """Mixin for mapping types with all the indexing hoo-hah.

    Add this mixin to your DjangoMappingType subclass and it gives you
    super indexing power.

    """

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

            cls.get_model().objects.order_by('id').values_list('id', flat=True)

        :returns: iterable of ids of objects to be indexed

        """
        model = cls.get_model()
        return model.objects.order_by('id').values_list('id', flat=True)

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

            .. Note::

               If you don't provide an ``id_``, then ElasticSearch
               will make up an id for your document and it'll look like
               a character name from a Lovecraft novel.

        :arg bulk: Whether or not this is part of a bulk indexing.  If
            this is, you must provide an ES with the `es` argument,
            too.
        :arg force_insert: TODO
        :arg es: The ES to use. If you don't specify an ES, it'll
            use `elasticutils.contrib.django.get_es()`.

        :raises ValueError: if `bulk` is True, but `es` is None.

        .. Note::

           After you add things to the index, make sure to refresh the
           index by calling ``refresh_index()``---it doesn't happen
           automatically.


        TODO: add example.

        """
        if bulk and es is None:
            raise ValueError('bulk is True, but es is None')

        if es is None:
            es = get_es()

        es.index(
            document, index=cls.get_index(),
            doc_type=cls.get_mapping_type_name(),
            id=id_, bulk=bulk, force_insert=force_insert)

    @classmethod
    def unindex(cls, id_, es=None):
        """Removes a particular item from the search index.

        TODO: document this better.

        """
        if es is None:
            es = get_es()

        es.delete(cls.get_index(), cls.get_mapping_type_name(), id_)

    @classmethod
    def refresh_index(cls, timesleep=0, es=None):
        """Refreshes the index.

        TODO: document this better.

        """
        if es is None:
            es = get_es()

        es.refresh(cls.get_index(), timesleep=timesleep)
