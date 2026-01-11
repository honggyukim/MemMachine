#!/usr/bin/env python3

from memmachine import MemMachineClient
import json

# 1. Initialize the client
# Replace 'http://localhost:8080' with your server's URL if different.
client = MemMachineClient(base_url="http://localhost:8080")

# 2. Get or Create a Project
# Projects organize memories under an Organization.
try:
    # Get if there is an existing project
    project = client.get_project(
        org_id="my-org",
        project_id="hello-world-project",
    )
except Exception:
    # Otherwise, create a project.
    project = client.create_project(
        org_id="my-org",
        project_id="hello-world-project",
        description="My first MemMachine project"
    )

print(f"Working with project: {project.org_id}/{project.project_id}")

# 3. Create a Memory Interface
# A Memory interface is scoped to a specific user/agent/session context.
memory = project.memory(
    user_id="user-alice",
    agent_id="agent-bob",
    session_id="session-1"
)

# 4. Add Memories
# Add a user message
memory.add(
    content="My favorite color is blue.",
    role="user"
)

# Add an agent response
memory.add(
    content="I'll remember that your favorite color is blue.",
    role="assistant"
)

print("Memories added.")

# 5. Search Memories
# Search for the information we just added.
results = memory.search("What is my favorite color?")

print("\nSearch Results:")
print(json.dumps(results.content, indent=2))
#print(results.json())

# {
#   "status": 0,
#   "content": {
#     "episodic_memory": {
#       "long_term_memory": {
#         "episodes": []
#       },
#       "short_term_memory": {
#         "episodes": [
#           {
#             "content": "My favorite color is blue.",
#             "producer_id": "user",
#             "producer_role": "user",
#             "produced_for_id": "",
#             "episode_type": "message",
#             "metadata": null,
#             "created_at": "2026-01-11T02:38:02.441273Z",
#             "uid": "4",
#             "score": null
#           },
#           {
#             "content": "I'll remember that your favorite color is blue.",
#             "producer_id": "user",
#             "producer_role": "assistant",
#             "produced_for_id": "",
#             "episode_type": "message",
#             "metadata": null,
#             "created_at": "2026-01-11T02:38:02.601171Z",
#             "uid": "5",
#             "score": null
#           }
#         ],
#         "episode_summary": [
#           ""
#         ]
#       }
#     },
#     "semantic_memory": [
#       {
#         "set_id": "mem_session_my-org/hello-world-project",
#         "category": "profile",
#         "tag": "Demographic Information",
#         "feature_name": "color",
#         "value": "blue",
#         "metadata": {
#           "citations": null,
#           "id": "1",
#           "other": null
#         }
#       },
#       {
#         "set_id": "mem_session_my-org/hello-world-project",
#         "category": "profile",
#         "tag": "Assistive Response Preferences",
#         "feature_name": "favorite_color",
#         "value": "blue",
#         "metadata": {
#           "citations": null,
#           "id": "2",
#           "other": null
#         }
#       }
#     ]
#   }
# }
