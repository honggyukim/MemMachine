# MemMachine v2 Examples

```
examples/v2/
├── py/   Python SDK examples
└── sh/   curl-based shell scripts (no SDK required)
```

---

## py/ — Python SDK examples

### Prerequisites

```bash
pip install memmachine-client          # all examples
pip install memmachine-client openai   # 02_chatbot_with_memory.py only
```

```bash
export MEMORY_BACKEND_URL="http://localhost:8080"
```

| File | What it shows |
|------|---------------|
| [`01_quickstart.py`](py/01_quickstart.py) | Connect, store, and search memories in ~50 lines |
| [`02_chatbot_with_memory.py`](py/02_chatbot_with_memory.py) | OpenAI chatbot that remembers the user across turns |
| [`03_multi_user.py`](py/03_multi_user.py) | Per-user memory isolation in a shared project |
| [`04_memory_crud.py`](py/04_memory_crud.py) | Full add / search / list / delete lifecycle |
| [`05_rest_api.py`](py/05_rest_api.py) | Raw HTTP calls — no Python SDK needed |
| [`06_session_continuity.py`](py/06_session_continuity.py) | Memories persisting across independent sessions |
| [`07_context_manager.py`](py/07_context_manager.py) | Context manager, project lifecycle, cleanup |

#### 01 — Quickstart

```bash
python py/01_quickstart.py
```

Covers the three-line happy path:

```python
client  = MemMachineClient(base_url="http://localhost:8080")
project = client.get_or_create_project(org_id="my_org", project_id="demo")
memory  = project.memory(metadata={"user_id": "alice"})

memory.add("I love hiking in the mountains.", role="user")
result = memory.search("What outdoor activities do I enjoy?")
```

#### 02 — Chatbot with Memory

```bash
OPENAI_API_KEY=sk-... python py/02_chatbot_with_memory.py
```

Shows the core **search → inject → store** pattern for building a stateful LLM assistant:
1. **Before** generating a reply: `memory.search(user_input)` → inject into system prompt.
2. **After** generating a reply: `memory.add(user_input)` + `memory.add(assistant_reply)`.

#### 03 — Multi-User

```bash
python py/03_multi_user.py
```

One project serves many users. Each `project.memory(metadata={"user_id": "alice"})` call
creates an isolated view — searches on Alice's handle never return Bob's memories.
Also shows **group-level** shared memory via `metadata={"group_id": "eng_team"}`.

#### 04 — Memory CRUD

```bash
python py/04_memory_crud.py
```

Full lifecycle: `memory.add()` with rich metadata, `memory.search()` with and without
`filter_dict`, `memory.list()` with pagination, `memory.delete_episodic()`, and
`project.get_episode_count()`.

#### 05 — REST API

```bash
python py/05_rest_api.py
```

Direct `requests` calls to `/api/v2/*` — useful when you want to see the exact wire
format. Covers health, project CRUD, add, search (with SQL-like filter), and delete.

#### 06 — Session Continuity

```bash
python py/06_session_continuity.py
```

Simulates two independent runs with different `session_id`s but the same `user_id`.
Session 2 recalls everything stored in Session 1 without any shared in-memory state.

#### 07 — Context Manager & Lifecycle

```bash
python py/07_context_manager.py
```

Uses `with MemMachineClient(...) as client:` for safe resource cleanup. Creates a
temporary project, stores memories, reads `episode_count`, deletes the project, then
verifies the 404.

---

## sh/ — Shell scripts (curl + jq)

No Python or SDK required — only `curl` and `jq`.

```bash
export MEMORY_BACKEND_URL="http://127.0.0.1:8080"
```

| File | Endpoint | What it does |
|------|----------|-------------|
| [`01_health-check.sh`](sh/01_health-check.sh) | `GET /health` | Verify the server is reachable |
| [`02_create-project.sh`](sh/02_create-project.sh) | `POST /projects` | Create a project |
| [`03_get-project.sh`](sh/03_get-project.sh) | `POST /projects/get` | Retrieve project details |
| [`04_list-projects.sh`](sh/04_list-projects.sh) | `POST /projects/list` | List all projects |
| [`05_add-new-memory.sh`](sh/05_add-new-memory.sh) | `POST /memories` | Store a memory with metadata |
| [`06_search-memory.sh`](sh/06_search-memory.sh) | `POST /memories/search` | Search with type names and filter |
| [`07_delete-memory.sh`](sh/07_delete-memory.sh) | `POST /memories/episodic/delete` | Add a memory then delete it by captured UID |
| [`08_delete-project.sh`](sh/08_delete-project.sh) | `POST /projects/delete` | Delete the project |
| [`09_hello-memmachine.py`](sh/09_hello-memmachine.py) | SDK | End-to-end Python SDK smoke test |
| [`10_run-all.sh`](sh/10_run-all.sh) | all | Run 01–08 in order; prints pass/fail summary |

Run the full suite:

```bash
./sh/10_run-all.sh
# Passed: 8  Failed: 0
```

---

## Core Concepts

```
Organization (org_id)
  └── Project (project_id)          ← memory boundary
        └── Memory handle
              metadata:
                user_id    → per-user isolation
                agent_id   → per-agent isolation
                group_id   → shared team memory
                session_id → per-session context
```

**Episodic memory** – the raw conversation log (Neo4j graph).
**Semantic memory** – facts and preferences extracted by the server (PostgreSQL + vectors).
Both are searched simultaneously by default via `memory.search(query)`.

### Filter strings

Metadata keys become search filters automatically. You can add extra filters:

```python
memory.search(
    "What technology stack does the user prefer?",
    filter_dict={"category": "tech"},   # AND-ed with user_id filter from metadata
)
```

The raw REST filter format is SQL-like:

```
metadata.user_id='alice' AND category='tech'
```
