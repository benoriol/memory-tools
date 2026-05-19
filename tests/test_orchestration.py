"""Orchestration: operator-context, prompt composition, runner plumbing.

End-to-end runs of the sub-agent are gated on CLAUDE_CODE_OAUTH_TOKEN
being set (and `claude-agent-sdk` installed). Unit tests below use a
stubbed runner so the SDK is never actually called.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from memory_graph.embed import FakeEmbedder
from memory_graph.orchestration.operator import (
    OPERATOR_DIRNAME,
    OPERATOR_FILE,
    operator_path,
    read_operator_context,
    write_operator_context,
)
from memory_graph.orchestration.runner import (
    DEFAULT_TOOL_NAMES,
    build_sdk_tools,
    compose_system_prompt,
    load_prompt,
)
from memory_graph.primitives import Store


@pytest.fixture()
def s(store: Path):
    with Store(store, embedder=FakeEmbedder(dim=32)) as instance:
        yield instance


# -- operator-context -------------------------------------------------------


def test_read_operator_context_creates_default(store: Path):
    text = read_operator_context(store)
    assert "Operator context" in text
    p = operator_path(store)
    assert p.exists()
    assert p.parent.name == OPERATOR_DIRNAME
    assert p.name == OPERATOR_FILE


def test_write_operator_context_round_trip(store: Path):
    write_operator_context(store, "Custom content here.\n")
    assert read_operator_context(store) == "Custom content here.\n"


def test_read_operator_context_idempotent_after_default(store: Path):
    first = read_operator_context(store)
    second = read_operator_context(store)
    assert first == second  # didn't overwrite


# -- prompts ----------------------------------------------------------------


def test_prompts_are_packaged():
    for name in ("system", "remember", "retrieve", "compact"):
        text = load_prompt(name)
        assert len(text) > 100, f"prompt '{name}' is suspiciously short"


def test_compose_system_prompt_concatenates_sections(s: Store):
    write_operator_context(s.root, "## My custom map\n\nCluster X here.\n")
    prompt = compose_system_prompt("remember", s.root)
    assert "memory specialist" in prompt.lower()
    assert "Task: remember" in prompt
    assert "Cluster X here" in prompt


def test_compose_system_prompt_includes_each_task(s: Store):
    for task in ("remember", "retrieve", "compact"):
        prompt = compose_system_prompt(task, s.root)
        assert f"Task: {task}" in prompt


# -- SDK tool wrappers ------------------------------------------------------


def test_build_sdk_tools_matches_default_names(s: Store):
    pytest.importorskip("claude_agent_sdk")
    tools = build_sdk_tools(s)
    names = {getattr(t, "name", None) for t in tools}
    assert set(DEFAULT_TOOL_NAMES) == names


def test_build_sdk_tools_search_returns_text_content(s: Store):
    pytest.importorskip("claude_agent_sdk")
    s.capture(title="t", summary="alpha bravo", body="b", kind="capture")
    tools = build_sdk_tools(s)
    search_tool = next(t for t in tools if t.name == "search")
    import asyncio

    result = asyncio.run(search_tool.handler({"query": "alpha bravo", "k": 5}))
    assert "content" in result
    blocks = result["content"]
    assert blocks and blocks[0]["type"] == "text"
    # Body should contain the captured note's id (some 26-char ULID).
    assert "alpha bravo" in blocks[0]["text"] or "id" in blocks[0]["text"]


# -- end-to-end (opt-in) ----------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="set CLAUDE_CODE_OAUTH_TOKEN to run a real sub-agent end-to-end",
)
def test_remember_end_to_end(s: Store):
    from memory_graph.orchestration import remember

    result = remember(
        "Today we tried cursor-based pagination on /ingest and it cut "
        "p95 latency from 800ms to 90ms at 5k req/s. We decided to keep "
        "it for new endpoints.",
        store=s,
    )
    assert isinstance(result, str) and len(result) > 0
    # And at least one note should have landed.
    assert s.status()["total_nodes"] >= 1
