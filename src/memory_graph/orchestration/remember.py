"""`remember(dump)` — decompose + write."""

from __future__ import annotations

from memory_graph.orchestration.runner import (
    REMEMBER_EFFORT,
    REMEMBER_MODEL,
    SubAgentResult,
    run_subagent,
    run_subagent_sync,
)
from memory_graph.primitives import Store


async def remember(dump: str, store: Store) -> SubAgentResult:
    """Hand `dump` to the memory sub-agent and return its result.

    Uses Sonnet at low effort (REMEMBER_MODEL/REMEMBER_EFFORT). The
    sub-agent decomposes the dump, searches for connections, writes
    new notes via `capture_batch`, and supersedes any contradictions.

    Must be awaited from inside an event loop (e.g. an MCP tool handler).
    For truly sync callers (CLI), use `remember_sync`.
    """
    return await run_subagent(
        task="remember",
        user_message=dump,
        store=store,
        model=REMEMBER_MODEL,
        effort=REMEMBER_EFFORT,
    )


def remember_sync(dump: str, store: Store) -> SubAgentResult:
    """Sync wrapper for callers NOT inside an event loop (CLI digest)."""
    return run_subagent_sync(
        task="remember",
        user_message=dump,
        store=store,
        model=REMEMBER_MODEL,
        effort=REMEMBER_EFFORT,
    )
