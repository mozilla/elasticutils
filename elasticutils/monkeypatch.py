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
                # Go through all the possible sections of item looking
                # for 'ok' and adding an additional 'status'.
                for key, val in item.items():
                    if 'ok' in val:
                        val['status'] = 201
                return item

            ret = fun(self, *args, **kwargs)
            if 'items' in ret:
                ret['items'] = [fix_item(item) for item in ret['items']]
            return ret
        return _fixed_bulk

    Elasticsearch.bulk = normalize_bulk_return(Elasticsearch.bulk)
