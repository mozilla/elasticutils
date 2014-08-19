.. _installation:

==============
 Installation
==============

Requirements
============

ElasticUtils requires:

* Python 2.6, 2.7, 3.3 or 3.4

* elasticsearch-py >= 0.4.3 < 1.0 and its dependencies

* Elasticsearch 0.90, 1.0 or 1.1

  This does not work with versions of Elasticsearch older than
  0.90 or newer than 1.1.


Installation
============

There are a few ways to install ElasticUtils:


From PyPI
---------

Do::

    $ pip install elasticutils


From git
--------

Do::

    $ git clone git://github.com/mozilla/elasticutils.git
    $ cd elasticutils
    $ python setup.py install
