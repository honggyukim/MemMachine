"""
MemMachine v2 - Context Manager & Resource Cleanup

Shows how to use `MemMachineClient` as a context manager so the underlying
HTTP session is always closed cleanly, and demonstrates project lifecycle
management (create → use → delete).

Prerequisites:
    pip install memmachine-client

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"

Run:
    python 07_context_manager.py
"""

import os

import requests

from memmachine_client import MemMachineClient

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")


def main() -> None:
    # The `with` block guarantees client.close() is called on exit (even on error).
    with MemMachineClient(base_url=MEMORY_BACKEND_URL) as client:

        # ------------------------------------------------------------------
        # Create a temporary project for this run
        # ------------------------------------------------------------------
        project = client.get_or_create_project(
            org_id="my_org",
            project_id="temp_project_lifecycle",
            description="Temporary project — will be deleted at the end",
        )
        print(f"Created: {project}")

        memory = project.memory(metadata={"user_id": "test_user"})

        # Store a couple of memories
        memory.add("Temporary fact A.", role="user")
        memory.add("Temporary fact B.", role="user")

        count_before = project.get_episode_count()
        print(f"Episode count before delete: {count_before}")

        # ------------------------------------------------------------------
        # List all projects to confirm our project is visible
        # ------------------------------------------------------------------
        all_projects = client.list_projects()
        project_ids = [f"{p.org_id}/{p.project_id}" for p in all_projects]
        print(f"All projects: {project_ids}")

        # ------------------------------------------------------------------
        # Refresh project metadata from server
        # ------------------------------------------------------------------
        project.refresh()
        print(f"After refresh — description: {project.description!r}")

        # ------------------------------------------------------------------
        # Clean up: delete the project (and all its memories)
        # ------------------------------------------------------------------
        project.delete()
        print("Project deleted.")

        # Verify it no longer exists
        try:
            client.get_project(org_id="my_org", project_id="temp_project_lifecycle")
            print("ERROR: project still exists!")
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                print("Confirmed: project no longer exists (404).")
            else:
                raise

    print("Client closed cleanly (context manager exited).")


if __name__ == "__main__":
    main()
