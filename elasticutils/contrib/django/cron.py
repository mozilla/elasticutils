from itertools import islice

from celery.task.sets import TaskSet


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


def reindex_objects(model, chunk_size=150):
    """Creates methods that reindex all the objects in a model.

    For example in your ``myapp.cron.py`` you can do::

        index_all_mymodels = cronjobs.register(reindex_objects(mymodel))

    and it will create a commandline callable task for you, e.g.::

        ./manage.py cron index_all_mymodels

    """
    def job():
        from elasticutils import tasks

        ids = list(model.objects.values_list('id', flat=True))
        ts = [tasks.index_objects.subtask(args=[chunk])
              for chunk in chunked(sorted(ids), chunk_size)]
        TaskSet(ts).apply_async()

    return job
