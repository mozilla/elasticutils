"""
This is a sample program that uses Elasticsearch (from elasticsearch-py)
object to create an index, create a mapping, and index some data. Then
it uses ElasticUtils S to show some behavior.
"""

from elasticutils import get_es, S

from elasticsearch.helpers import bulk_index

URL = 'localhost'
INDEX = 'fooindex'
DOCTYPE = 'testdoc'
 

# This creates an elasticsearch.Elasticsearch object which we can use
# to do all our indexing.
es = get_es(urls=[URL])
 
# First, delete the index if it exists.
es.indices.delete(index=INDEX, ignore=404)
 
# Define the mapping for the doctype 'testdoc'. It's got an id field,
# a title which is analyzed, and two fields that are lists of tags, so
# we don't want to analyze them.
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
 
# Create the index 'testdoc' mapping.
es.indices.create(INDEX, body={'mappings': mapping})


# Let's index some documents and make them available for searching.
documents = [
    {'_id': 1,
     'title': 'Deleting cookies',
     'topics': ['cookies', 'privacy'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'_id': 2,
     'title': 'What is a cookie?',
     'topics': ['cookies', 'privacy'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'_id': 3,
     'title': 'Websites say cookies are blocked - Unblock them',
     'topics': ['cookies', 'privacy', 'websites'],
     'product': ['Firefox', 'Firefox for mobile', 'Boot2Gecko']},
    {'_id': 4,
     'title': 'Awesome Bar',
     'topics': ['tips', 'search', 'user interface'],
     'product': ['Firefox']},
    {'_id': 5,
     'title': 'Flash',
     'topics': ['flash'],
     'product': ['Firefox']}
    ]

bulk_index(es, documents, index=INDEX, doc_type=DOCTYPE)
es.indices.refresh(index=INDEX)


# Now let's do some basic queries.

# Let's build a basic S that looks at our Elasticsearch cluster and
# the index and doctype we just indexed our documents in.
basic_s = S().es(urls=[URL]).indexes(INDEX).doctypes(DOCTYPE)

# How many documents are in our index?
print basic_s.count()
# Prints:
# 5

# Print articles with 'cookie' in the title.
print [item['title']
       for item in basic_s.query(title__text='cookie')]
# Prints:
# [u'Deleting cookies', u'What is a cookie?',
#  u'Websites say cookies are blocked - Unblock them']

# Print articles with 'cookie' in the title that are related to
# websites.
print [item['title']
       for item in basic_s.query(title__text='cookie')
                          .filter(topics='websites')]
# Prints:
# [u'Websites say cookies are blocked - Unblock them']

# Print articles in the 'search' topic.
print [item['title']
       for item in basic_s.filter(topics='search')]
# Prints:
# [u'Awesome Bar']

# Do a query and use the highlighter to denote the matching text.
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
