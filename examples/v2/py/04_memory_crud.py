"""
MemMachine v2 - Memory CRUD Operations

Full create / read / list / delete lifecycle for both episodic and semantic
memories, plus metadata-filtered search.

Prerequisites:
    pip install memmachine-client

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"

Run:
    python 04_memory_crud.py
"""

import os

from memmachine_client import MemMachineClient
from memmachine_common.api import MemoryType

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")


def main() -> None:
    client = MemMachineClient(base_url=MEMORY_BACKEND_URL)

    # Always use get_or_create so the script is re-runnable
    project = client.get_or_create_project(
        org_id="my_org",
        project_id="crud_demo",
    )
    memory = project.memory(metadata={"user_id": "crud_user"})

    # ------------------------------------------------------------------
    # 1. CREATE — add memories with rich metadata
    # ------------------------------------------------------------------
    print("=== 1. ADD memories ===")

    entries = [
        ("I prefer Python for scripting tasks.",   {"category": "tech",     "type": "preference"}),
        ("I attended PyCon 2024 in Pittsburgh.",   {"category": "events",   "type": "fact"}),
        ("I am learning Rust on weekends.",        {"category": "tech",     "type": "learning"}),
        ("My favourite food is sushi.",            {"category": "food",     "type": "preference"}),
        ("I visited Tokyo in 2023.",               {"category": "travel",   "type": "fact"}),
    ]

    stored_ids: list[str] = []
    for content, meta in entries:
        results = memory.add(content, role="user", metadata=meta)
        uid = results[0].uid if results else "?"
        stored_ids.append(uid)
        print(f"  + {content!r}  uid={uid}")

    print()

    # ------------------------------------------------------------------
    # 2. READ — semantic search (all memories)
    # ------------------------------------------------------------------
    print("=== 2. SEARCH (no filter) ===")
    result = memory.search("What do I know about technology?", limit=5)
    episodes = (
        result.content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    for ep in episodes:
        print(f"  [{ep.get('role')}] {ep['content']}")

    print()

    # ------------------------------------------------------------------
    # 3. FILTERED search — only 'tech' category
    # ------------------------------------------------------------------
    print("=== 3. FILTERED SEARCH (category=tech) ===")
    result = memory.search(
        "programming languages",
        limit=5,
        filter_dict={"category": "tech"},
    )
    episodes = (
        result.content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    for ep in episodes:
        print(f"  {ep['content']}")

    print()

    # ------------------------------------------------------------------
    # 4. LIST — paginate through episodic memories
    # ------------------------------------------------------------------
    print("=== 4. LIST episodic memories (page 0, size 10) ===")
    list_result = memory.list(
        memory_type=MemoryType.Episodic,
        page_size=10,
        page_num=0,
    )
    items = list_result.content if hasattr(list_result, "content") else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                print(f"  uid={item.get('uid', '?')}  {item.get('content', '')[:60]}")
    print(f"  Total items returned: {len(items) if isinstance(items, list) else '?'}")

    print()

    # ------------------------------------------------------------------
    # 5. DELETE — remove one specific episodic memory by UID
    # ------------------------------------------------------------------
    # Grab the first stored uid (if available)
    if stored_ids and stored_ids[0] != "?":
        target_uid = stored_ids[0]
        print(f"=== 5. DELETE episodic memory uid={target_uid} ===")
        try:
            memory.delete_episodic(episodic_id=target_uid)
            print("  Deleted successfully.")
        except Exception as exc:
            print(f"  Delete failed (may not exist as standalone episode): {exc}")
    else:
        print("=== 5. DELETE (skipped – no valid uid) ===")

    print()

    # ------------------------------------------------------------------
    # 6. Verify deletion — search should return fewer results
    # ------------------------------------------------------------------
    print("=== 6. SEARCH after delete ===")
    result = memory.search("Python scripting", limit=5)
    episodes = (
        result.content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    print(f"  Results: {len(episodes)} episode(s) returned.")

    print()

    # ------------------------------------------------------------------
    # 7. Project-level helpers
    # ------------------------------------------------------------------
    print("=== 7. PROJECT helpers ===")
    count = project.get_episode_count()
    print(f"  Episode count for project: {count}")

    projects = client.list_projects()
    print(f"  Total projects on server: {len(projects)}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
