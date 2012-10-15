import logging

from django.conf import settings
from celery.decorators import task

from elasticutils.contrib.django import get_es


log = logging.getLogger('elasticutils')


@task
def index_objects(model, ids, **kw):
    """Models can asynchronously update their ES index.

    If a model extends SearchMixin, it can add a post_save hook like so::

        @receiver(dbsignals.post_save, sender=MyModel)
        def update_search_index(sender, instance, **kw):
            from elasticutils import tasks
            tasks.index_objects.delay(sender, [instance.id])

    """
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    log.debug('Indexing objects %s-%s. [%s]' % (ids[0], ids[-1], len(ids)))
    qs = model.objects.filter(id__in=ids)
    for item in qs:
        model.index(model.extract_document(item.id, item),
                    bulk=True, id_=item.id, es=es)

    es.flush_bulk(forced=True)
    model.refresh_index(es=es)


@task
def unindex_objects(model, ids, **kw):
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    for id_ in ids:
        log.debug('Removing object [%s.%d] from search index.' % (model, id_))
        model.unindex(id=id_, es=es)
