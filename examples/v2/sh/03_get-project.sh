#!/bin/sh -x
# Retrieve details of an existing project.
# Usage: ./get-project.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"

curl -s -X POST "${BASE_URL}/api/v2/projects/get" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "project_id": "my-first-project"
  }' | jq
