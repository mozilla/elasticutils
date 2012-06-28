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
    if settings.ES_DISABLED:
        return
    es = get_es()
    log.info('Indexing objects %s-%s. [%s]' % (ids[0], ids[-1], len(ids)))
    qs = model.objects.filter(id__in=ids)
    for item in qs:
        model.index(item.fields(), bulk=True, id=item.id)
    es.flush_bulk(forced=True)


@task
def unindex_objects(model, ids, **kw):
    if settings.ES_DISABLED:
        return
    for id in ids:
        log.info('Removing object [%s.%d] from search index.' % (model, id))
        elasticutils.get_es().delete(model._get_index(), model._meta.db_table, id)
