#!/bin/sh -x
# Add a temporary memory, capture its UID from the response, then delete it.
# No manual ID needed — the UID is obtained automatically from the add call.
# Usage: ./delete-memory.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"

# Step 1: Add a temporary memory and capture the returned UID.
ADD_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v2/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "project_id": "my-first-project",
    "messages": [
      {
        "content": "Temporary memory to be deleted immediately.",
        "role": "user",
        "metadata": {
          "user_id": "user-alice",
          "type": "temp"
        }
      }
    ]
  }')

echo "${ADD_RESPONSE}" | jq .

EPISODIC_ID=$(echo "${ADD_RESPONSE}" | jq -r '.results[0].uid')

if [ -z "${EPISODIC_ID}" ] || [ "${EPISODIC_ID}" = "null" ]; then
  echo "ERROR: could not extract UID from add response" >&2
  exit 1
fi

echo "Captured uid: ${EPISODIC_ID}"

# Step 2: Delete the memory using the captured UID.
curl -s -X POST "${BASE_URL}/api/v2/memories/episodic/delete" \
  -H "Content-Type: application/json" \
  -d "{
    \"org_id\": \"my-org\",
    \"project_id\": \"my-first-project\",
    \"episodic_id\": \"${EPISODIC_ID}\",
    \"episodic_ids\": []
  }" | jq
