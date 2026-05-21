"""`retrieve(query)` — explore + synthesize."""

from __future__ import annotations

from memory_graph.orchestration.runner import (
    RETRIEVE_EFFORT,
    RETRIEVE_MODEL,
    SubAgentResult,
    run_subagent,
    run_subagent_sync,
)
from memory_graph.primitives import Store


async def retrieve(
    query_text: str,
    store: Store,
    *,
    intent: str = "decide",
) -> SubAgentResult:
    """Hand `query_text` to the memory sub-agent and return its result.

    Uses Haiku at low effort (RETRIEVE_MODEL/RETRIEVE_EFFORT) — read-only
    graph navigation needs no write discipline, and Haiku matched Sonnet
    on quality at ~3× the speed in the retrieval benchmark.

    `intent` is one of "decide" / "explore" / "verify"; it shapes which
    edge types the sub-agent walks.
    """
    user_message = f"intent: {intent}\n\n{query_text}"
    return await run_subagent(
        task="retrieve",
        user_message=user_message,
        store=store,
        model=RETRIEVE_MODEL,
        effort=RETRIEVE_EFFORT,
    )


def retrieve_sync(
    query_text: str,
    store: Store,
    *,
    intent: str = "decide",
) -> SubAgentResult:
    user_message = f"intent: {intent}\n\n{query_text}"
    return run_subagent_sync(
        task="retrieve",
        user_message=user_message,
        store=store,
        model=RETRIEVE_MODEL,
        effort=RETRIEVE_EFFORT,
    )
