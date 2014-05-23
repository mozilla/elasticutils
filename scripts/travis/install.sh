#!/bin/bash

# Installs Elasticsearch
#
# Requires ESVER environment variable to be set.

set -e

echo "Installing Elasticsearch $ESVER" >&2
wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-$ESVER.tar.gz
tar xzvf elasticsearch-$ESVER.tar.gz
