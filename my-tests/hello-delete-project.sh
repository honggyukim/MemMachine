#!/bin/sh -x

curl -X POST "http://127.0.0.1:8080/api/v2/projects/delete" \
-H "Content-Type: application/json" \
-d '{
  "org_id": "my-org",
  "project_id": "hello-world-project"
}' | jq
