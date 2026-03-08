"""
MemMachine v2 - Memory-Augmented Chatbot (OpenAI)

This example shows the core pattern for building a chatbot that remembers
past conversations across sessions.

Pattern:
  1. Before each reply, search MemMachine for relevant past context.
  2. Inject that context into the system prompt.
  3. After the reply, store both the user message and assistant reply.

Prerequisites:
    pip install memmachine-client openai

Setup:
    export MEMORY_BACKEND_URL="http://localhost:8080"
    export OPENAI_API_KEY="sk-..."

Run:
    python 02_chatbot_with_memory.py
"""

import os

from memmachine_client import MemMachineClient
from openai import OpenAI

MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"

# Fixed user/agent IDs for this demo; a real app would derive these from auth context.
USER_ID = "demo_user"
AGENT_ID = "assistant_v1"


def get_relevant_context(memory, query: str) -> str:
    """Search MemMachine and format results as a context block."""
    result = memory.search(query, limit=6)
    content = result.content

    lines: list[str] = []

    # Episodic short-term memory (recent messages)
    episodes = (
        content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episodes", [])
    )
    if episodes:
        lines.append("Recent conversation history:")
        for ep in episodes:
            role = ep.get("role", "user")
            lines.append(f"  [{role}] {ep['content']}")

    # Long-term summarised memory
    summaries = (
        content.get("episodic_memory", {})
        .get("short_term_memory", {})
        .get("episode_summary", [])
    )
    if summaries:
        lines.append("Past session summary:")
        for s in summaries:
            lines.append(f"  - {s}")

    # Semantic memory (extracted facts / preferences)
    semantic = content.get("semantic_memory", [])
    if semantic:
        lines.append("Known user facts:")
        for item in semantic:
            lines.append(
                f"  [{item.get('category')}/{item.get('tag')}] "
                f"{item.get('feature_name')} = {item.get('value')}"
            )

    return "\n".join(lines)


def chat(openai_client: OpenAI, memory, user_input: str) -> str:
    """One turn of the conversation with memory-augmented context."""
    # Retrieve relevant context before generating a response
    context = get_relevant_context(memory, user_input)

    system_prompt = "You are a helpful personal assistant with long-term memory."
    if context:
        system_prompt += f"\n\nWhat you remember about this user:\n{context}"

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    assistant_reply = response.choices[0].message.content

    # Persist both turns to MemMachine
    memory.add(user_input, role="user")
    memory.add(assistant_reply, role="assistant")

    return assistant_reply


def main() -> None:
    if not OPENAI_API_KEY:
        print("Set OPENAI_API_KEY to run this example.")
        return

    # --- MemMachine setup ---
    mm_client = MemMachineClient(base_url=MEMORY_BACKEND_URL)
    project = mm_client.get_or_create_project(
        org_id="my_org",
        project_id="chatbot_demo",
    )
    memory = project.memory(
        metadata={"user_id": USER_ID, "agent_id": AGENT_ID}
    )

    # --- OpenAI setup ---
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    print("Memory-Augmented Chatbot  (type 'quit' to exit)\n")

    # Simulate a conversation
    turns = [
        "Hi! My name is Alice and I love hiking.",
        "I'm also learning Python.",
        "What do you know about me so far?",
        "Recommend a hiking destination for me.",
    ]

    for user_input in turns:
        print(f"You: {user_input}")
        reply = chat(openai_client, memory, user_input)
        print(f"Bot: {reply}\n")

    print("Conversation complete. Memories are persisted for future sessions.")


if __name__ == "__main__":
    main()
