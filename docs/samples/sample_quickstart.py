"""
This is a sample program that uses pyelasticsearch ElasticSearch
object to create an index, create a mapping, and index some data. Then
it uses ElasticUtils S to show some behavior with facets.
"""

from elasticutils import get_es, S

from pyelasticsearch.exceptions import ElasticHttpNotFoundError


URL = 'http://localhost:9200'
INDEX = 'fooindex'
DOCTYPE = 'testdoc'
 

# This creates a pyelasticsearch ElasticSearch object which we can use
# to do all our indexing.
es = get_es(urls=[URL])
 
# First, delete the index.
try:
    es.delete_index(INDEX)
except ElasticHttpNotFoundError:
    # Getting this here means the index doesn't exist, so there's
    # nothing to delete.
    pass
 
# Define the mapping for the doctype 'testdoc'. It's got an id field,
# a title which is analyzed, and two fields that are lists of tags, so
# we don't want to analyze them.
#
# Note: The alternative for the tags is to analyze them and use the
# 'keyword' analyzer. Both not analyzing and using the keyword
# analyzer treats the values as a single term rather than tokenizing
# them and treating as multiple terms.
mapping = {
    DOCTYPE: {
        'properties': {
            'id': {'type': 'integer'},
            'title': {'type': 'string', 'analyzer': 'snowball'},
            'topics': {'type': 'string'},
            'product': {'type': 'string', 'index': 'not_analyzed'},
            }
        }
    }
 
# This uses pyelasticsearch ElasticSearch.create_index to create the
# index with the specified mapping for 'testdoc'.
es.create_index(INDEX, settings={'mappings': mapping})


# This indexes a series of documents each is a Python dict.
documents = [
    {'id': 1,
     'title': 'Deleting cookies',
     'topics': ['cookies', 'privacy'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'id': 2,
     'title': 'What is a cookie?',
     'topics': ['cookies', 'privacy', 'basic'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'id': 3,
     'title': 'Websites say cookies are blocked - Unblock them',
     'topics': ['cookies', 'privacy', 'websites'],
     'product': ['Firefox', 'Firefox for mobile', 'Boot2Gecko']},
    {'id': 4,
     'title': 'Awesome Bar',
     'topics': ['tips', 'search', 'basic', 'user interface'],
     'product': ['Firefox']},
    {'id': 5,
     'title': 'Flash',
     'topics': ['flash'],
     'product': ['Firefox']}
    ]

es.bulk_index(INDEX, DOCTYPE, documents, id_field='id')

# ElasticSearch will refresh the indexes and make those documents
# available for querying in a second or so (it's configurable in
# ElasticSearch), but we want them available right now, so we refresh
# the index.
es.refresh(INDEX)

# Ok. We've created an index and tossed some stuff in it. Let's
# do some basic queries.

# Let's build a basic S that looks at the right instance of
# ElasticSearch, index, and doctype.
basic_s = S().es(urls=[URL]).indexes(INDEX).doctypes(DOCTYPE)

# How many documents are in our index?
print basic_s.count()
# Prints:
# 5

# Let's get all the cookie articles.
print [item['title']
       for item in basic_s.query(title__text='cookie')]
# Prints:
# [u'Deleting cookies', u'What is a cookie?',
# u'Websites say cookies are blocked - Unblock them']

# Let's see cookie articles for websites.
print [item['title']
       for item in basic_s.query(title__text='cookie')
                          .filter(topics='websites')]
# Prints:
# [u'Websites say cookies are blocked - Unblock them']

# Let's see all articles in the 'basic' topic.
print [item['title']
       for item in basic_s.filter(topics='basic')]
# Prints:
# [u'Awesome Bar', u'What is a cookie?']

# Let's do a query and use the highlighter to denote the matching
# text.
print [(item['title'], item._highlight['title'])
       for item in basic_s.query(title__text='cookie').highlight('title')]
# Prints:
# [
#    (u'Deleting cookies', [u'Deleting <em>cookies</em>']),
#    (u'What is a cookie?', [u'What is a <em>cookie</em>?']),
#    (u'Websites say cookies are blocked - Unblock them',
#       [u'Websites say <em>cookies</em> are blocked - Unblock them']
#    )
# ]


# That's the gist of it!
