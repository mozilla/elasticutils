import logging

import elasticutils
from celeryutils import task

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
    es = elasticutils.get_es()
    log.info('Indexing objects %s-%s. [%s]' % (ids[0], ids[-1], len(ids)))
    qs = model.filter(id__in=ids)
    for item in qs:
        model.index(item.fields(), bulk=True, id=item.id)
    es.flush_bulk(forced=True)
