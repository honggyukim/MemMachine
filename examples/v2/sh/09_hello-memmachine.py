#!/usr/bin/env python3
"""
hello-memmachine.py — end-to-end smoke test for the MemMachine Python SDK.

Run:
    pip install memmachine-client
    export MEMORY_BACKEND_URL="http://localhost:8080"   # optional, defaults shown
    python hello-memmachine.py
"""

import json
import os

from memmachine_client import MemMachineClient

BASE_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")

# 1. Initialize the client
client = MemMachineClient(base_url=BASE_URL)

# Optional: verify the server is reachable before doing anything else.
health = client.health_check()
print(f"Server health: {health}")

# 2. Get or Create a Project
# get_or_create_project() is idempotent — safe to call on every startup.
project = client.get_or_create_project(
    org_id="my-org",
    project_id="hello-world-project",
    description="My first MemMachine project",
)
print(f"Working with project: {project.org_id}/{project.project_id}")

# 3. Create a Memory Interface
# Pass context as a metadata dict.  Every add() and search() call on this
# handle will automatically scope to user-alice / agent-bob / session-1.
memory = project.memory(
    metadata={
        "user_id": "user-alice",
        "agent_id": "agent-bob",
        "session_id": "session-1",
    }
)

# 4. Add Memories
results_user = memory.add(
    content="My favorite color is blue.",
    role="user",
)
results_asst = memory.add(
    content="I'll remember that your favorite color is blue.",
    role="assistant",
)
uid_user = results_user[0].uid if results_user else "?"
uid_asst = results_asst[0].uid if results_asst else "?"
print(f"Stored user message    uid={uid_user}")
print(f"Stored assistant reply uid={uid_asst}")

# 5. Search Memories
# The metadata context (user_id, agent_id, session_id) is applied as a
# filter automatically, so only alice's memories are returned.
result = memory.search("What is my favorite color?", limit=5)

print("\nSearch Results:")
print(json.dumps(result.content, indent=2))

# Expected output shape:
# {
#   "episodic_memory": {
#     "long_term_memory":  {"episodes": []},
#     "short_term_memory": {
#       "episodes": [
#         {"content": "My favorite color is blue.",               "role": "user",      "uid": "4", ...},
#         {"content": "I'll remember that your favorite color…",  "role": "assistant", "uid": "5", ...}
#       ],
#       "episode_summary": [""]
#     }
#   },
#   "semantic_memory": [
#     {"category": "profile", "tag": "Demographic Information",        "feature_name": "color",          "value": "blue"},
#     {"category": "profile", "tag": "Assistive Response Preferences", "feature_name": "favorite_color", "value": "blue"}
#   ]
# }

# 6. Episode count
count = project.get_episode_count()
print(f"\nTotal episodes in project: {count}")
