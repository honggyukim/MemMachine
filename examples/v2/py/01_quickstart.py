"""
MemMachine v2 - Quickstart

The minimal example to get started: connect to a running MemMachine server,
store a few memories, and search them back.

Prerequisites:
    pip install memmachine-client

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"   # or use --base-url flag

Run:
    python 01_quickstart.py
"""

import os

from memmachine_client import MemMachineClient

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")


def main() -> None:
    # 1. Connect to the server
    client = MemMachineClient(base_url=MEMORY_BACKEND_URL)

    health = client.health_check()
    print(f"Server status: {health.get('status', 'ok')}")

    # 2. Get or create a project (org + project scope all memory)
    project = client.get_or_create_project(
        org_id="my_org",
        project_id="quickstart",
        description="Quickstart example project",
    )
    print(f"Project: {project}")

    # 3. Create a memory handle for a specific user + session
    memory = project.memory(
        metadata={
            "user_id": "alice",
            "session_id": "session_001",
        }
    )

    # 4. Store some memories
    facts = [
        ("I love hiking in the mountains.", "user"),
        ("I am learning Python and machine learning.", "user"),
        ("I prefer tea over coffee.", "user"),
        ("Understood! I'll remember your preference for tea.", "assistant"),
    ]
    for content, role in facts:
        results = memory.add(content, role=role)
        uid = results[0].uid if results else "?"
        print(f"  Stored [{role}]: {content!r}  -> uid={uid}")

    # 5. Search for relevant memories
    print()
    for query in [
        "What outdoor activities do I enjoy?",
        "What drink does the user prefer?",
    ]:
        result = memory.search(query, limit=3)
        episodes = (
            result.content.get("episodic_memory", {})
            .get("short_term_memory", {})
            .get("episodes", [])
        )
        print(f"Query: {query!r}")
        for ep in episodes:
            print(f"  [{ep.get('role', '?')}] {ep['content']}")
        print()


if __name__ == "__main__":
    main()
