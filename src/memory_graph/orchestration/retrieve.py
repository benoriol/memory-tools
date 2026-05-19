"""`retrieve(query)` — explore + synthesize."""

from __future__ import annotations

from memory_graph.orchestration.runner import run_subagent_sync
from memory_graph.primitives import Store


def retrieve(
    query_text: str,
    store: Store,
    *,
    intent: str = "decide",
) -> str:
    """Hand `query_text` to the memory sub-agent and return its synthesis.

    `intent` is one of "decide" / "explore" / "verify"; it shapes which
    edge types the sub-agent walks. The result is a focused prose
    synthesis with cited ids (see `prompts/retrieve.md`).
    """
    user_message = f"intent: {intent}\n\n{query_text}"
    return run_subagent_sync(
        task="retrieve",
        user_message=user_message,
        store=store,
    )
