"""`remember(dump)` — decompose + write."""

from __future__ import annotations

from memory_graph.orchestration.runner import run_subagent, run_subagent_sync
from memory_graph.primitives import Store


async def remember(dump: str, store: Store) -> str:
    """Hand `dump` to the memory sub-agent and return its synthesis.

    The sub-agent decomposes the dump, searches for connections, writes
    new notes via `capture_batch`, and supersedes any contradictions.
    Returns a structured-ish text response (see `prompts/remember.md`).

    Must be awaited from inside an event loop (e.g. an MCP tool handler).
    For truly sync callers (CLI), use `remember_sync`.
    """
    return await run_subagent(
        task="remember",
        user_message=dump,
        store=store,
    )


def remember_sync(dump: str, store: Store) -> str:
    """Sync wrapper for callers NOT inside an event loop (CLI digest)."""
    return run_subagent_sync(
        task="remember",
        user_message=dump,
        store=store,
    )
