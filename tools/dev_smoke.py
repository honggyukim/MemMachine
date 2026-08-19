"""End-to-end smoke check for a MemMachine development server.

Creates a project, stores a few episodes and searches them back, either by
calling the v2 REST API directly or by going through the memmachine-client
library. Both modes drive the same server and print the same report.

Normally invoked through ``dev-sqlite.sh smoke``, which also restarts the
server between the two searches. See that script for why the restart matters.
It can also be pointed at any running server, for example::

    uv run python tools/dev_smoke.py ingest --base-url http://127.0.0.1:8080
    uv run python tools/dev_smoke.py search --mode client --project my_project

Run both steps in the same mode. The REST calls pass ``metadata`` in the
request, which selects the session, while the client library attaches it to
each message and turns it into a search filter, staying in the default
session. Each mode therefore finds its own episodes but not the other's.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from typing import Any

import httpx

EPISODES = (
    "I go hiking in the mountains every weekend.",
    "I drink espresso while coding late at night.",
    "My favorite programming language is C.",
    "The weather today is cloudy.",
)
QUERY = "outdoor activities in nature"
TOP_K = 5
TIMEOUT = 300


def report(episodic: dict[str, Any]) -> None:
    """Print the long- and short-term episodes of a search result."""
    for name in ("long_term_memory", "short_term_memory"):
        episodes = episodic[name]["episodes"]
        print(f"    {name}: {len(episodes)} episode(s)")
        for episode in episodes:
            score = episode.get("score")
            prefix = "      " if score is None else f"      score={score:.4f}  "
            print(prefix + episode["content"])


class RestRunner:
    """Talks to the v2 REST API with plain HTTP requests.

    Each method is one POST and nothing else, so the equivalent curl command is
    given above it. SHOW_CURL=1 prints the same commands with the actual ids
    filled in, ready to paste.
    """

    def __init__(self, base_url: str, meta: dict[str, Any], *, show_curl: bool):
        self._base_url = base_url.rstrip("/")
        self._meta = meta
        self._show_curl = show_curl

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/api/v2{path}"
        if self._show_curl:
            body = json.dumps(payload)
            print(
                f"    $ curl -X POST {url} \\\n"
                f"        -H 'Content-Type: application/json' \\\n"
                f"        -d {shlex.quote(body)}"
            )
        response = httpx.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def create_project(self) -> None:
        # curl -X POST http://127.0.0.1:8080/api/v2/projects \
        #   -H 'Content-Type: application/json' \
        #   -d '{"org_id": "smoke", "project_id": "smoke_1"}'
        self._post(
            "/projects",
            {"org_id": self._meta["org_id"], "project_id": self._meta["project_id"]},
        )

    def store(self) -> None:
        # curl -X POST http://127.0.0.1:8080/api/v2/memories \
        #   -H 'Content-Type: application/json' \
        #   -d '{"org_id": "smoke", "project_id": "smoke_1",
        #        "metadata": {"user_id": "smoke_user"},
        #        "messages": [{"content": "I go hiking in the mountains every weekend.",
        #                      "role": "user"}]}'
        #
        # "messages" is required and is a list even for a single episode; a
        # "content"/"role" pair at the top level is rejected with a 422.
        messages = [{"content": episode, "role": "user"} for episode in EPISODES]
        self._post("/memories", {**self._meta, "messages": messages})

    def search(self) -> None:
        # curl -X POST http://127.0.0.1:8080/api/v2/memories/search \
        #   -H 'Content-Type: application/json' \
        #   -d '{"org_id": "smoke", "project_id": "smoke_1",
        #        "metadata": {"user_id": "smoke_user"},
        #        "query": "outdoor activities in nature", "top_k": 5}'
        #
        # The result cap is "top_k" (SearchMemoriesSpec.top_k). A "limit" key is
        # accepted without complaint and then ignored, leaving the default of 10.
        result = self._post(
            "/memories/search", {**self._meta, "query": QUERY, "top_k": TOP_K}
        )
        report(result["content"]["episodic_memory"])


class ClientRunner:
    """Performs the same steps through the memmachine-client library."""

    def __init__(self, base_url: str, meta: dict[str, Any], *, show_curl: bool):
        from memmachine_client import MemMachineClient

        _ = show_curl  # the client builds its own requests
        self._client = MemMachineClient(base_url=base_url, timeout=TIMEOUT)
        self._project = self._client.get_or_create_project(
            org_id=meta["org_id"], project_id=meta["project_id"]
        )
        self._memory = self._project.memory(metadata=meta["metadata"])

    def create_project(self) -> None:
        # get_or_create_project already ran in __init__.
        return

    def store(self) -> None:
        for episode in EPISODES:
            self._memory.add(episode, role="user")

    def search(self) -> None:
        episodic = self._memory.search(QUERY, limit=TOP_K).content.episodic_memory
        if episodic is None:
            raise RuntimeError("search returned no episodic memory")
        report(episodic.model_dump())


RUNNERS = {"rest": RestRunner, "client": ClientRunner}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("ingest", "search"))
    parser.add_argument("--mode", choices=tuple(RUNNERS), default="rest")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--org", default="smoke")
    parser.add_argument("--project", default="smoke")
    parser.add_argument("--user", default="smoke_user")
    parser.add_argument(
        "--show-curl",
        action="store_true",
        help="print the equivalent curl command before each request (rest mode)",
    )
    args = parser.parse_args()

    meta = {
        "org_id": args.org,
        "project_id": args.project,
        "metadata": {"user_id": args.user},
    }
    runner = RUNNERS[args.mode](args.base_url, meta, show_curl=args.show_curl)

    if args.step == "ingest":
        runner.create_project()
        print(f"    created project {args.org}/{args.project}")
        runner.store()
        print(f"    stored {len(EPISODES)} episodes")

    runner.search()
    return 0


if __name__ == "__main__":
    sys.exit(main())
