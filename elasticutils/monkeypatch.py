from functools import wraps

from elasticsearch import Elasticsearch


_monkeypatched_es = False


def monkeypatch_es():
    """Monkey patch for elasticsearch-py 1.0+ to make it work with ES 0.90

    1. tweaks elasticsearch.client.bulk to normalize return status codes

    .. Note::

       We can nix this whe we drop support for ES 0.90.

    """
    if _monkeypatched_es:
        return

    def normalize_bulk_return(fun):
        """Set's "ok" based on "status" if "status" exists"""
        @wraps(fun)
        def _fixed_bulk(self, *args, **kwargs):
            def fix_item(item):
                if 'ok' in item['index']:
                    item['index']['status'] = 201
                return item

            ret = fun(self, *args, **kwargs)
            if 'items' in ret:
                ret['items'] = [fix_item(item) for item in ret['items']]
            return ret
        return _fixed_bulk

    Elasticsearch.bulk = normalize_bulk_return(Elasticsearch.bulk)
