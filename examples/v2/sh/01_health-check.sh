#!/bin/sh -x
# Check that the MemMachine server is up and healthy.
# Usage: ./health-check.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"

curl -s "${BASE_URL}/api/v2/health" | jq
