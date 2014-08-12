from functools import wraps

from elasticsearch import Elasticsearch, VERSION


_monkeypatched_es = False


def monkeypatch_es():
    """Monkey patch for elasticsearch-py 0.4.5 to make it work with ES 1.0

    1. tweaks elasticsearch.client.bulk to normalize return status codes

    """
    if _monkeypatched_es:
        return

    if VERSION == (0, 4, 5):
        def normalize_bulk_return(fun):
            """Set's "ok" based on "status" if "status" exists"""
            @wraps(fun)
            def _fixed_bulk(self, *args, **kwargs):
                def fix_item(item):
                    if 'status' in item['index']:
                        item['index']['ok'] = (
                            200 <= item['index']['status'] < 300)
                    return item

                ret = fun(self, *args, **kwargs)
                if 'items' in ret:
                    ret['items'] = [fix_item(item) for item in ret['items']]
                return ret
            return _fixed_bulk

        Elasticsearch.bulk = normalize_bulk_return(Elasticsearch.bulk)
