import logging
from functools import wraps

import elasticsearch

from django.conf import settings
from django.shortcuts import render
from django.utils.decorators import decorator_from_middleware_with_args

from elasticutils import F, InvalidFieldActionError, MLT, NoModelError  # noqa
from elasticutils import S as BaseS
from elasticutils import get_es as base_get_es
from elasticutils import Indexable as BaseIndexable
from elasticutils import MappingType as BaseMappingType


log = logging.getLogger('elasticutils')


ES_EXCEPTIONS = (
    elasticsearch.ElasticsearchException,
)


def get_es(**overrides):
    """Return a elasticsearch Elasticsearch object using settings
    from ``settings.py``.

    :arg overrides: Allows you to override defaults to create the
        ElasticSearch object. You can override any of the arguments
        isted in :py:func:`elasticutils.get_es`.

    For example, if you wanted to create an ElasticSearch with a
    longer timeout to a different cluster, you'd do:

    >>> from elasticutils.contrib.django import get_es
    >>> es = get_es(urls=['http://some_other_cluster:9200'], timeout=30)

    """
    defaults = {
        'urls': settings.ES_URLS,
        'timeout': getattr(settings, 'ES_TIMEOUT', 5)
        }

    defaults.update(overrides)
    return base_get_es(**defaults)


def es_required(fun):
    """Wrap a callable and return None if ES_DISABLED is False.

    This also adds an additional `es` argument to the callable
    giving you an ElasticSearch instance to use.

    """
    @wraps(fun)
    def wrapper(*args, **kw):
        if getattr(settings, 'ES_DISABLED', False):
            log.debug('Search disabled for %s.' % fun)
            return

        return fun(*args, es=get_es(), **kw)
    return wrapper


class ESExceptionMiddleware(object):
    """Middleware to handle Elasticsearch errors.

    HTTP 501
      Returned when ``ES_DISABLED`` is True.

    HTTP 503
      Returned when any elasticsearch exception is thrown.

      Template variables:

      * error: A string version of the exception thrown.

    :arg disabled_template: The template to use when ES_DISABLED is True.

        Defaults to ``elasticutils/501.html``.

    :arg error_template: The template to use when Elasticsearch isn't
        working properly, is missing an index, or something along
        those lines.

        Defaults to ``elasticutils/503.html``.


    .. Note::

       In order to use the included templates, you must add
       ``elasticutils.contrib.django`` to ``INSTALLED_APPS``.

    """

    def __init__(self, disabled_template=None, error_template=None):
        self.disabled_template = (
            disabled_template or 'elasticutils/501.html')
        self.error_template = (
            error_template or 'elasticutils/503.html')

    def process_request(self, request):
        if getattr(settings, 'ES_DISABLED', False):
            response = render(request, self.disabled_template)
            response.status_code = 501
            return response

    def process_exception(self, request, exception):
        if issubclass(exception.__class__, ES_EXCEPTIONS):
            response = render(request, self.error_template,
                              {'error': exception})
            response.status_code = 503
            return response


"""
The following decorator wraps a Django view and handles Elasticsearch errors.

This wraps a Django view and returns 501 or 503 status codes and
pages if things go awry.

See the above middleware for explanation of the arguments.

Examples::

    # This creates a home_view and decorates it to use the
    # default templates.

    @es_required_or_50x()
    def home_view(request):
        ...


    # This creates a search_view and overrides the templates

    @es_required_or_50x(disabled_template='search/es_disabled.html',
                        error_template('search/es_down.html')
    def search_view(request):
        ...

"""
es_required_or_50x = decorator_from_middleware_with_args(
    ESExceptionMiddleware)


class S(BaseS):
    """S that's based on Django settings"""
    def __init__(self, mapping_type):
        """Create and return an S.

        :arg mapping_type: class; the mapping type that this S is
            based on

        .. Note::

           The :py:class:`elasticutils.S` doesn't require the
           `mapping_type` argument, but the
           :py:class:`elasticutils.contrib.django.S` does.

        """
        return super(S, self).__init__(mapping_type)

    def get_es(self, default_builder=get_es):
        """Returns the elasticsearch Elasticsearch object to use.

        This uses the django get_es builder by default which takes
        into account settings in ``settings.py``.

        """
        return super(S, self).get_es(default_builder=default_builder)

    def get_indexes(self, default_indexes=None):
        """Returns the list of indexes to act on based on ES_INDEXES setting

        """
        doctype = self.type.get_mapping_type_name()
        indexes = (settings.ES_INDEXES.get(doctype) or
                   settings.ES_INDEXES['default'])
        if isinstance(indexes, basestring):
            indexes = [indexes]
        return super(S, self).get_indexes(default_indexes=indexes)

    def get_doctypes(self, default_doctypes=None):
        """Returns the doctypes (or mapping type names) to use."""
        doctypes = self.type.get_mapping_type_name()
        if isinstance(doctypes, basestring):
            doctypes = [doctypes]
        return super(S, self).get_doctypes(default_doctypes=doctypes)


class MappingType(BaseMappingType):
    """MappingType that ties to Django ORM models

    You probably want to subclass this and override at least
    `get_model()`.

    """
    def get_object(self):
        """Returns the database object for this result

        By default, this is::

            self.get_model().objects.get(pk=self._id)

        """
        return self.get_model().objects.get(pk=self._id)

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

        By default, this is::

            cls.get_model()._meta.db_table

        Override this if you want to compute the mapping type name
        differently.

        :returns: mapping type string

        """
        return cls.get_model()._meta.db_table

    @classmethod
    def search(cls):
        """Returns a typed S for this class.

        :returns: an `S` for this DjangoMappingType

        """
        return S(cls)


class Indexable(BaseIndexable):
    """MappingType mixin that has indexing bits

    Add this mixin to your MappingType subclass and it gives you super
    indexing power.

    """

    @classmethod
    def get_es(cls, **overrides):
        """Returns an ElasticSearch object using Django settings

        Override this if you need special functionality.

        :arg overrides: Allows you to override defaults to create the
            ElasticSearch object. You can override any of the arguments
            listed in :py:func:`elasticutils.get_es`.

        :returns: a elasticsearch `Elasticsearch` instance

        """
        return get_es(**overrides)

    @classmethod
    def get_indexable(cls):
        """Returns the queryset of ids of all things to be indexed.

        Defaults to::

            cls.get_model().objects.order_by('id').values_list(
                'id', flat=True)

        :returns: iterable of ids of objects to be indexed

        """
        model = cls.get_model()
        return model.objects.order_by('id').values_list('id', flat=True)
