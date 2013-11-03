"""
This is a sample program that uses Elasticsearch (from elasticsearch-py)
object to create an index, create a mapping, and index some data. Then
it uses ElasticUtils S to show some behavior with facets.
"""

from elasticutils import get_es, S

from elasticsearch.helpers import bulk_index

URL = 'localhost'
INDEX = 'fooindex'
DOCTYPE = 'testdoc'
 

# This creates an elasticsearch.Elasticsearch object which we can use
# to do all our indexing.
es = get_es(urls=[URL])
 
# First, delete the index, ignore possible 404 - it means the index doesn't
# exist, so there's nothing to delete.
es.indices.delete(index=INDEX, ignore=404)
 
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
            'title': {'type': 'string'},
            'topics': {'type': 'string'},
            'product': {'type': 'string', 'index': 'not_analyzed'},
            }
        }
    }
 
# create the index with defined mappings
es.indices.create(index=INDEX, body={'mappings': mapping})


# This indexes a series of documents each is a Python dict.
documents = [
    {'_id': 1,
     'title': 'Deleting cookies',
     'topics': ['cookies', 'privacy'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'_id': 2,
     'title': 'What is a cookie?',
     'topics': ['cookies', 'privacy', 'basic'],
     'product': ['Firefox', 'Firefox for mobile']},
    {'_id': 3,
     'title': 'Websites say cookies are blocked - Unblock them',
     'topics': ['cookies', 'privacy', 'websites'],
     'product': ['Firefox', 'Firefox for mobile', 'Boot2Gecko']},
    {'_id': 4,
     'title': 'Awesome Bar',
     'topics': ['tips', 'search', 'basic', 'user interface'],
     'product': ['Firefox']},
    {'_id': 5,
     'title': 'Flash',
     'topics': ['flash'],
     'product': ['Firefox']}
    ]

bulk_index(es, documents, index=INDEX, doc_type=DOCTYPE)

# Elasticsearch will refresh the indexes and make those documents
# available for querying in a second or so (it's configurable in
# Elasticsearch), but we want them available right now, so we refresh
# the index.
es.indices.refresh(index=INDEX)

# Let's build a basic S that looks at the right Elasticsearch cluster,
# index and doctype.
basic_s = S().es(urls=[URL]).indexes(INDEX).doctypes(DOCTYPE).values_dict()
 
# Now let's see facet counts for all the products.
s = basic_s.facet('product')

print s.facet_counts()
# Pretty-printed output:
# {u'product': [
#    {u'count': 5, u'term': u'Firefox'},
#    {u'count': 3, u'term': u'Firefox for mobile'},
#    {u'count': 1, u'term': u'Boot2Gecko'}
#    ]}

# Let's do a query for 'cookie' and do a facet count.
print s.query(title__text='cookie').facet_counts()
# Pretty-printed output:
# {u'product': [
#    {u'count': 1, u'term': u'Firefox for mobile'},
#    {u'count': 1, u'term': u'Firefox'}
#    ]}

# Note that the facet_counts are affected by the query.

# Let's do a filter for 'flash' in the topic.
print s.filter(topics='flash').facet_counts()
# Pretty-printed output:
# {u'product': [
#    {u'count': 5, u'term': u'Firefox'},
#    {u'count': 3, u'term': u'Firefox for mobile'},
#    {u'count': 1, u'term': u'Boot2Gecko'}
#    ]}

# Note that the facet_counts are NOT affected by filters.

# Let's do a filter for 'flash' in the topic, and specify
# filtered=True.
print s.facet('product', filtered=True).filter(topics='flash').facet_counts()
# Pretty-printed output:
# {u'product': [
#    {u'count': 1, u'term': u'Firefox'}
#    ]}

# Using filtered=True causes the facet_counts to be affected by the
# filters.

# We've done a bunch of faceting on a field that is not
# analyzed. Let's look at what happens when we try to use facets on a
# field that is analyzed.
print basic_s.facet('topics').facet_counts()
# Pretty-printed output:
# {u'topics': [
#    {u'count': 3, u'term': u'privacy'},
#    {u'count': 3, u'term': u'cookies'},
#    {u'count': 2, u'term': u'basic'},
#    {u'count': 1, u'term': u'websites'},
#    {u'count': 1, u'term': u'user'},
#    {u'count': 1, u'term': u'tips'},
#    {u'count': 1, u'term': u'search'},
#    {u'count': 1, u'term': u'interface'},
#    {u'count': 1, u'term': u'flash'}
#    ]}

# Note how the facet counts shows 'user' and 'interface' as two
# separate terms even though they're a single topic for document with
# id=4. When that document is indexed, the topic field is analyzed and
# the default analyzer tokenizes it splitting it into two terms.
#
# Moral of the story is that you want fields you facet on to be
# analyzed as keyword fields or not analyzed at all.
