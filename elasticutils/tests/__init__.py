from distutils.version import LooseVersion
from functools import wraps

from nose import SkipTest

from elasticutils.estestcase import ESTestCase  # noqa


def facet_counts_dict(qs, field):
    return dict((t['term'], t['count']) for t in qs.facet_counts()[field])


def require_version(minimum_version):
    """Skip the test if the Elasticsearch version is less than specified.

    :arg minimum_version: string; the minimum Elasticsearch version required

    """

    def decorated(test):
        """Decorator to only run the test if ES version is greater or
        equal than specified.

        """

        @wraps(test)
        def test_with_version(self):
            "Only run the test if ES version is not less than specified."
            actual_version = self.get_es().info()['version']['number']

            if LooseVersion(actual_version) >= LooseVersion(minimum_version):
                test(self)
            else:
                raise SkipTest

        return test_with_version

    return decorated
