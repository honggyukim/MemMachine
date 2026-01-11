#!/bin/sh -x

curl -X POST "http://127.0.0.1:8080/api/v2/memories" \
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
        "type": "fact",
        "topic": "testing"
      }
    }
  ]
}' | jq
