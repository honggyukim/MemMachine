"""
MemMachine v2 - REST API (no Python SDK)

Shows how to call the MemMachine HTTP API directly with `requests`.
Useful if you are not using Python, or want to understand the raw wire format.

All endpoints live under:  POST /api/v2/...

Prerequisites:
    pip install requests

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"

Run:
    python 05_rest_api.py
"""

import json
import os

import requests

BASE_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080").rstrip("/")
API = f"{BASE_URL}/api/v2"

HEADERS = {"Content-Type": "application/json"}

ORG_ID = "my_org"
PROJECT_ID = "rest_api_demo"
USER_ID = "rest_user"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pp(label: str, data) -> None:
    """Pretty-print a labelled JSON blob."""
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, default=str))


def post(path: str, body: dict) -> dict:
    resp = requests.post(f"{API}{path}", json=body, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Health check  (GET)
# ---------------------------------------------------------------------------

def health_check() -> None:
    resp = requests.get(f"{API}/health", timeout=10)
    resp.raise_for_status()
    pp("Health", resp.json())


# ---------------------------------------------------------------------------
# 2. Project management
# ---------------------------------------------------------------------------

def create_project() -> None:
    body = {
        "org_id": ORG_ID,
        "project_id": PROJECT_ID,
        "description": "REST API demo project",
        "config": {"embedder": "", "reranker": ""},
    }
    try:
        data = post("/projects", body)
        pp("Create project", data)
    except requests.HTTPError as exc:
        if exc.response.status_code == 409:
            print("Project already exists — continuing.")
        else:
            raise


def get_project() -> None:
    data = post("/projects/get", {"org_id": ORG_ID, "project_id": PROJECT_ID})
    pp("Get project", data)


def list_projects() -> None:
    resp = requests.post(f"{API}/projects/list", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    pp("List projects", resp.json())


# ---------------------------------------------------------------------------
# 3. Add memories
# ---------------------------------------------------------------------------

def add_memories() -> list[str]:
    """Add a batch of messages and return their UIDs."""
    messages = [
        {
            "content": "I enjoy reading science fiction novels.",
            "role": "user",
            "metadata": {"user_id": USER_ID, "category": "hobbies"},
        },
        {
            "content": "My preferred programming language is Go.",
            "role": "user",
            "metadata": {"user_id": USER_ID, "category": "tech"},
        },
        {
            "content": "I live in Berlin and love the city.",
            "role": "user",
            "metadata": {"user_id": USER_ID, "category": "personal"},
        },
    ]

    body = {
        "org_id": ORG_ID,
        "project_id": PROJECT_ID,
        "messages": messages,
        "types": [],  # empty = store as both episodic + semantic
    }

    data = post("/memories", body)
    pp("Add memories response", data)

    uids = [r["uid"] for r in data.get("results", [])]
    print(f"\nStored UIDs: {uids}")
    return uids


# ---------------------------------------------------------------------------
# 4. Search memories
# ---------------------------------------------------------------------------

def search_memories(query: str, filter_str: str = "") -> None:
    body = {
        "org_id": ORG_ID,
        "project_id": PROJECT_ID,
        "query": query,
        "top_k": 5,
        "types": ["episodic", "semantic"],
        "expand_context": 0,
    }
    if filter_str:
        body["filter"] = filter_str

    data = post("/memories/search", body)

    # Extract short-term episodes for display
    episodes = (
        data.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    print(f"\nSearch: {query!r}  filter={filter_str!r}")
    if episodes:
        for ep in episodes:
            print(f"  [{ep.get('role')}] {ep['content']}")
    else:
        print("  (no results)")


# ---------------------------------------------------------------------------
# 5. Delete a memory
# ---------------------------------------------------------------------------

def delete_episodic(uid: str) -> None:
    body = {
        "org_id": ORG_ID,
        "project_id": PROJECT_ID,
        "episodic_id": uid,
        "episodic_ids": [],
    }
    data = post("/memories/episodic/delete", body)
    pp(f"Delete episodic {uid}", data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Connecting to {BASE_URL}\n")

    health_check()
    create_project()
    get_project()
    list_projects()

    uids = add_memories()

    search_memories("What are my hobbies?")
    search_memories(
        "What technology do I use?",
        filter_str=f"metadata.user_id='{USER_ID}' AND category='tech'",
    )

    if uids:
        delete_episodic(uids[0])

    search_memories("science fiction")  # Should return fewer results after delete

    print("\nDone.")


if __name__ == "__main__":
    main()
