from celery.task.sets import TaskSet
from celeryutils import chunked


def reindex_objects(model, chunk_size=150):
    """Creates methods that reindex all the objects in a model.

    For example in your ``myapp.cron.py`` you can do::
        index_all_mymodels = cronjobs.register(reindex_objects(mymodel))

    and it will create a commandline callable task for you (e.g.)::

        ./manage.py cron index_all_mymodels

    """
    def job():
        from elasticutils import tasks

        ids = (model.objects.values_list('id', flat=True))
        ts = [tasks.index_objects.subtask(args=[chunk])
              for chunk in chunked(sorted(list(ids)), chunk_size)]
        TaskSet(ts).apply_async()

    return job
