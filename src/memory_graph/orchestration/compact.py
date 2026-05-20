"""`compact(scope?)` — regional consolidation pass."""

from __future__ import annotations

from memory_graph.orchestration.runner import (
    COMPACT_MODEL,
    run_subagent,
    run_subagent_sync,
)
from memory_graph.primitives import Store


def _message(scope: str | None) -> str:
    if scope:
        return f"scope: {scope}\n\nProceed with consolidation."
    return "scope: (none given — choose the most-overdue region)"


async def compact(store: Store, *, scope: str | None = None) -> str:
    """Run a consolidation pass over a cluster or recent activity.

    `scope` is "cluster:X", "topic:Y", "recent", or None (sub-agent
    picks). Returns a summary of what changed.

    Must be awaited from inside an event loop. Use `compact_sync` from
    sync contexts.
    """
    return await run_subagent(
        task="compact",
        user_message=_message(scope),
        store=store,
        model=COMPACT_MODEL,
    )


def compact_sync(store: Store, *, scope: str | None = None) -> str:
    return run_subagent_sync(
        task="compact",
        user_message=_message(scope),
        store=store,
        model=COMPACT_MODEL,
    )
