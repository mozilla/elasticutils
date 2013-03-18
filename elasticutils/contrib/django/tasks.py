import logging

from django.conf import settings
from celery.decorators import task


log = logging.getLogger('elasticutils')


@task
def index_objects(mapping_type, ids, **kw):
    """Index documents of a specified mapping type.

    This allows for asynchronous indexing.

    If a mapping_type extends Indexable, you can add a ``post_save``
    hook for the model that it's based on like this::

        @receiver(dbsignals.post_save, sender=MyModel)
        def update_in_index(sender, instance, **kw):
            from elasticutils.contrib.django import tasks
            tasks.index_objects.delay(MyMappingType, [instance.id])


    .. Warning::

       This uses bulk indexing. If you pass in, say, 10,000 ids
       then it will build a single list of 10,000 documents and
       then bulk index them all at once.

       Therefore, you want to do the chunking. If you have 10,000
       documents to index, you should create `x` celery tasks with `y`
       sized chunks each where `y` is whatever you think is an
       appropriate number.

    """
    if settings.ES_DISABLED:
        return

    log.debug('Indexing objects {0}-{1}. [{2}]'.format(
            ids[0], ids[-1], len(ids)))

    # Get the model this mapping type is based on.
    model = mapping_type.get_model()

    # Retrieve all the objects that we're going to index and do it in
    # bulk.
    documents = []
    for obj in model.objects.filter(id__in=ids):
        try:
            documents.append(mapping_type.extract_document(obj.id, obj))
        except Exception as exc:
            print 'GAH!', repr(exc)
            log.exception('Unable to extract document {0}'.format(obj))

    mapping_type.bulk_index(documents, id_field='id')


@task
def unindex_objects(mapping_type, ids, **kw):
    """Remove documents of a specified mapping_type from the index.

    This allows for asynchronous deleting.

    If a mapping_type extends Indexable, you can add a ``pre_delete``
    hook for the model that it's based on like this::

        @receiver(dbsignals.pre_delete, sender=MyModel)
        def remove_from_index(sender, instance, **kw):
            from elasticutils.contrib.django import tasks
            tasks.unindex_objects.delay(MyMappingType, [instance.id])

    """
    if settings.ES_DISABLED:
        return

    for id_ in ids:
        mapping_type.unindex(id_)
