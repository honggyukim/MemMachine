#!/bin/sh -x
# Search memories in a project.
# Usage: ./search-memory.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)
#
# The "filter" field uses SQL-like syntax: key='value' AND key='value'
# Types must be lowercase: "episodic" and "semantic".

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"

curl -s -X POST "${BASE_URL}/api/v2/memories/search" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "project_id": "my-first-project",
    "query": "simple test memory",
    "top_k": 5,
    "types": ["episodic", "semantic"],
    "filter": "metadata.user_id='\''user-alice'\''",
    "expand_context": 0
  }' | jq
