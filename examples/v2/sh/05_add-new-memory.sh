#!/bin/sh -x
# Add memories to a project.
# Usage: ./add-new-memory.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"

curl -s -X POST "${BASE_URL}/api/v2/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "project_id": "my-first-project",
    "messages": [
      {
        "content": "This is a simple test memory.",
        "producer": "user-alice",
        "produced_for": "agent-bob",
        "role": "user",
        "timestamp": "2025-11-24T10:00:00Z",
        "metadata": {
          "user_id": "user-alice",
          "type": "fact",
          "topic": "testing"
        }
      }
    ]
  }' | jq
