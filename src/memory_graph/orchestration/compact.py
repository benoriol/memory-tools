"""`compact(scope?)` — regional consolidation pass."""

from __future__ import annotations

from memory_graph.orchestration.runner import (
    COMPACT_EFFORT,
    COMPACT_MAX_TURNS,
    COMPACT_MODEL,
    SubAgentResult,
    run_subagent,
    run_subagent_sync,
)
from memory_graph.primitives import Store


def _message(scope: str | None) -> str:
    if scope:
        return f"scope: {scope}\n\nProceed with consolidation."
    return "scope: (none given — choose the most-overdue region)"


async def compact(store: Store, *, scope: str | None = None) -> SubAgentResult:
    """Run a consolidation pass over a cluster or recent activity.

    Uses Opus at medium effort with a higher max_turns ceiling — cross-
    cluster reasoning is the heaviest of the three orchestration tools.
    """
    return await run_subagent(
        task="compact",
        user_message=_message(scope),
        store=store,
        model=COMPACT_MODEL,
        effort=COMPACT_EFFORT,
        max_turns=COMPACT_MAX_TURNS,
    )


def compact_sync(store: Store, *, scope: str | None = None) -> SubAgentResult:
    return run_subagent_sync(
        task="compact",
        user_message=_message(scope),
        store=store,
        model=COMPACT_MODEL,
        effort=COMPACT_EFFORT,
        max_turns=COMPACT_MAX_TURNS,
    )
