"""
MemMachine v2 - Multi-User Memory Isolation

Demonstrates how a single project can serve many users while keeping each
user's memories completely isolated from the others.

Key insight: The `metadata={"user_id": ...}` passed to `project.memory()` is
automatically applied as a filter on every `search()` call, so user A never
sees user B's memories even when they share the same project.

Prerequisites:
    pip install memmachine-client

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"

Run:
    python 03_multi_user.py
"""

import os

from memmachine_client import MemMachineClient

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def print_search(label: str, result) -> None:
    episodes = (
        result.content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    hits = [ep["content"] for ep in episodes]
    print(f"  {label}: {hits if hits else '(no results)'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    client = MemMachineClient(base_url=MEMORY_BACKEND_URL)
    project = client.get_or_create_project(
        org_id="my_org",
        project_id="multi_user_demo",
        description="Shared project with per-user memory isolation",
    )

    # Each user gets their own Memory handle.  The metadata is embedded in
    # every add() and search() call automatically.
    users = {
        "alice": project.memory(metadata={"user_id": "alice", "agent_id": "support_bot"}),
        "bob":   project.memory(metadata={"user_id": "bob",   "agent_id": "support_bot"}),
        "carol": project.memory(metadata={"user_id": "carol", "agent_id": "support_bot"}),
    }

    # Store user-specific facts
    user_facts = {
        "alice": [
            "I am a frontend developer specialising in React.",
            "My favourite colour is blue.",
        ],
        "bob": [
            "I am a data scientist working with PyTorch.",
            "I prefer dark mode on all my devices.",
        ],
        "carol": [
            "I am a product manager focused on developer tools.",
            "I enjoy cycling on weekends.",
        ],
    }

    print("=== Storing per-user memories ===")
    for user, facts in user_facts.items():
        for fact in facts:
            users[user].add(fact, role="user")
            print(f"  [{user}] stored: {fact!r}")

    print()

    # Search — each user only finds their own memories
    print("=== Searching: 'What is my job?' ===")
    for user, memory in users.items():
        result = memory.search("What is my job?", limit=3)
        print_search(user, result)

    print()

    # Cross-user search isolation check
    print("=== Isolation check: Alice searches for 'PyTorch' (Bob's fact) ===")
    result = users["alice"].search("PyTorch data scientist", limit=3)
    print_search("alice (should be empty)", result)

    print()
    print("=== Bob searches for 'PyTorch data scientist' (his own fact) ===")
    result = users["bob"].search("PyTorch data scientist", limit=3)
    print_search("bob", result)

    print()

    # Group-level memory: shared between all members of a team
    print("=== Team-shared memory (group_id='eng_team') ===")
    team_memory = project.memory(metadata={"group_id": "eng_team"})
    team_memory.add("Our sprint goal is to ship the v2 API by Friday.", role="system")

    for user in ["alice", "bob"]:
        team_view = project.memory(
            metadata={"user_id": user, "group_id": "eng_team"}
        )
        result = team_view.search("What is the sprint goal?", limit=3)
        print_search(f"{user} sees sprint goal", result)


if __name__ == "__main__":
    main()
