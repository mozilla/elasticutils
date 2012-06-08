=======
Testing
=======

Testing elasticutils things in your code
========================================

`ESTestCase` can be subclassed in your apps testcases.

It does the following:

* If `ES_HOSTS` is empty it raises a `SkipTest`.
* `self.es` is available from the `ESTestCase` class and any subclasses.
* At the end of the Test Case the index is destroyed.
