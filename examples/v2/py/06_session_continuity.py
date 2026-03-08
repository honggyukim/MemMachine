"""
MemMachine v2 - Session Continuity

Demonstrates how memories persist across multiple independent sessions.
Session 1 stores facts about the user; Session 2 retrieves them without
any shared state — simulating a real restart or a second device.

Prerequisites:
    pip install memmachine-client

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"

Run:
    python 06_session_continuity.py
"""

import os
import uuid

from memmachine_client import MemMachineClient

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")

# Stable identifiers that survive across sessions
ORG_ID = "my_org"
PROJECT_ID = "continuity_demo"
USER_ID = "persistent_user"
AGENT_ID = "demo_agent"


def run_session_1(client: MemMachineClient) -> str:
    """
    First session: the user shares some facts.
    Returns the session_id so we can demonstrate it is NOT needed in session 2.
    """
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"=== Session 1  (id={session_id}) ===")

    project = client.get_or_create_project(org_id=ORG_ID, project_id=PROJECT_ID)
    memory = project.memory(
        metadata={
            "user_id": USER_ID,
            "agent_id": AGENT_ID,
            "session_id": session_id,
        }
    )

    facts = [
        "My name is Jordan.",
        "I work as a backend engineer at a fintech company.",
        "I prefer TypeScript for frontend and Python for backend.",
        "I am preparing for a marathon next spring.",
    ]
    for fact in facts:
        memory.add(fact, role="user")
        print(f"  [stored] {fact}")

    print(f"  Session 1 complete. {len(facts)} memories persisted.\n")
    return session_id


def run_session_2(client: MemMachineClient) -> None:
    """
    Second session (fresh start): no shared state with session 1.
    The user is identified only by user_id; memories from session 1 are recalled.
    """
    new_session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"=== Session 2  (id={new_session_id}) — fresh start ===")

    project = client.get_or_create_project(org_id=ORG_ID, project_id=PROJECT_ID)
    memory = project.memory(
        metadata={
            "user_id": USER_ID,
            "agent_id": AGENT_ID,
            "session_id": new_session_id,  # different session, same user
        }
    )

    queries = [
        "What is the user's name and job?",
        "What programming languages does the user like?",
        "What physical activity is the user training for?",
    ]

    for query in queries:
        result = memory.search(query, limit=3)
        episodes = (
            result.content.get("episodic_memory", {})
            .get("short_term_memory", {})
            .get("episodes", [])
        )
        print(f"\nQ: {query}")
        if episodes:
            for ep in episodes:
                print(f"  -> {ep['content']}")
        else:
            # Memories from session 1 may appear in long-term memory depending
            # on server configuration (short-term window size).
            long_term = (
                result.content.get("episodic_memory", {})
                .get("long_term_memory", {})
                .get("episodes", [])
            )
            if long_term:
                for ep in long_term:
                    print(f"  -> [long-term] {ep['content']}")
            else:
                print("  (no results — server may need time to index)")

    print()

    # Continue the conversation in session 2 — new memories stack on top
    memory.add("I also enjoy playing chess online.", role="user")
    memory.add("Noted! Chess is a great mental exercise.", role="assistant")
    print("Session 2: added new memories on top of session 1's context.")


def main() -> None:
    client = MemMachineClient(base_url=MEMORY_BACKEND_URL)
    client.health_check()

    session_1_id = run_session_1(client)
    print(f"(Session 1 id was: {session_1_id} — not used in session 2)\n")

    run_session_2(client)

    print("Done. Memories persist indefinitely until explicitly deleted.")


if __name__ == "__main__":
    main()
