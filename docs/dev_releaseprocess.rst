=================
 Release process
=================

1. Checkout master tip.

2. Check to make sure ``setup.py``, requirements files, and
   ``docs/installation.rst``  have correct version of
   elasticsearch-py.

3. Update version numbers in ``elasticutils/_version.py``.

   1. Set ``__version__`` to something like ``0.4``.
   2. Set ``__releasedate__`` to something like ``20120731``.

4. Update ``CONTRIBUTORS``, ``CHANGELOG``, ``MANIFEST.in``.

   Make sure to set the date for the release in CHANGELOG.

   Make sure requirements in ``setup.py``, ``docs/installation.rst``
   and ``CHANGELOG`` all match.

5. Verify correctness.

   1. Run tests.
   2. Build docs.
   3. Run sample programs in docs.
   4. Verify all that works.

6. Tag the release::

       $ git tag -a v0.4

   Copy the details from ``CHANGELOG`` into the tag comment.

7. Push everything::

       $ git push --tags official master

8. Update PyPI::

       $ rm -rf dist/*
       $ python setup.py sdist bdist_wheel
       $ twine upload dist/*

9. Update topic in ``#elasticutils``, blog post, twitter, etc.
