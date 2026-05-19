"""`compact(scope?)` — regional consolidation pass."""

from __future__ import annotations

from memory_graph.orchestration.runner import COMPACT_MODEL, run_subagent_sync
from memory_graph.primitives import Store


def compact(store: Store, *, scope: str | None = None) -> str:
    """Run a consolidation pass over a cluster or recent activity.

    `scope` is "cluster:X", "topic:Y", "recent", or None (sub-agent
    picks). Returns a summary of what changed.
    """
    user_message = (
        f"scope: {scope}\n\nProceed with consolidation."
        if scope
        else "scope: (none given — choose the most-overdue region)"
    )
    return run_subagent_sync(
        task="compact",
        user_message=user_message,
        store=store,
        model=COMPACT_MODEL,
    )
