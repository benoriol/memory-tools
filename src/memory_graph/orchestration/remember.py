"""`remember(dump)` — decompose + write."""

from __future__ import annotations

from memory_graph.orchestration.runner import run_subagent_sync
from memory_graph.primitives import Store


def remember(dump: str, store: Store) -> str:
    """Hand `dump` to the memory sub-agent and return its synthesis.

    The sub-agent decomposes the dump, searches for connections, writes
    new notes via `capture_batch`, and supersedes any contradictions.
    Returns a structured-ish text response (see `prompts/remember.md`).
    """
    return run_subagent_sync(
        task="remember",
        user_message=dump,
        store=store,
    )
