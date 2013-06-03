===============
 Documentation
===============

Conventions
===========

See the `docmentation page in the webdev bootcamp guide
<http://mozweb.readthedocs.org/en/latest/documentation.html>`_ for
documentation conventions.

The documentation is available in HTML and PDF forms at
`<http://elasticutils.readthedocs.org/>`_. This tracks documentation
in the master branch of the git repository. Because of this, it is
always up to date.

Also, of extreme high-priority hyperbole-ignoring importance:

*ElasticSearch* (camel-case)

    Refers to the pyelasticsearch ElasticSearch
    class and instances.

*Elasticsearch* (no camel-case)

    The Elasticsearch software.


Building the docs
=================

The documentation in `docs/` is built with `Sphinx
<http://sphinx.pocoo.org/>`_. To build HTML version of the
documentation, do::

    $ cd docs/
    $ make html
