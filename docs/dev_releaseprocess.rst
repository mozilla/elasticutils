=================
 Release process
=================

1. Checkout master tip.

2. Update version numbers in ``elasticutils/_version.py``.

   1. Set ``__version__`` to something like ``0.4``.
   2. Set ``__releasedate__`` to something like ``20120731``.

3. Update ``CONTRIBUTORS``, ``CHANGELOG``, ``MANIFEST.in``.

4. Verify correctness.

   1. Run tests.
   2. Build docs.
   3. Verify all that works.

5. Tag the release::

       $ git tag -a v0.4

6. Push everything::

       $ git push --tags official master

7. Update PyPI::

       $ python setup.py sdist upload

8. Update topic in ``#elasticutils``, blog post, twitter, etc.
