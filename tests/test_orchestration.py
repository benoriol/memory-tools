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


# -- SDK tool error envelope ------------------------------------------------


def test_sdk_tools_return_error_envelope_on_exception(s: Store):
    """Regression: when a tool's underlying call raises, the wrapper must
    return an isError envelope so the sub-agent sees a clear failure rather
    than a silent success it might paper over with hallucinated writes.
    """
    pytest.importorskip("claude_agent_sdk")
    import asyncio
    import json as _json

    from memory_graph.orchestration.runner import build_sdk_tools

    # Force capture() to blow up.
    def boom(*a, **kw):
        raise RuntimeError("simulated SQLite locked")

    s.capture = boom  # type: ignore[method-assign]
    tools = build_sdk_tools(s)
    capture_tool = next(t for t in tools if t.name == "capture")

    out = asyncio.run(
        capture_tool.handler({
            "title": "t", "summary": "s", "body": "b", "kind": "capture"
        })
    )
    assert out.get("isError") is True
    body = _json.loads(out["content"][0]["text"])
    assert "error" in body
    assert "RuntimeError" in body["error"]
    assert "simulated SQLite locked" in body["error"]


def test_sdk_tools_search_error_envelope(s: Store):
    """Same guarantee for the read-side tools — exceptions surface, not silenced."""
    pytest.importorskip("claude_agent_sdk")
    import asyncio
    import json as _json

    from memory_graph.orchestration.runner import build_sdk_tools

    def boom(*a, **kw):
        raise OSError("simulated fs failure")

    s.search = boom  # type: ignore[method-assign]
    tools = build_sdk_tools(s)
    search_tool = next(t for t in tools if t.name == "search")
    out = asyncio.run(search_tool.handler({"query": "anything"}))
    assert out.get("isError") is True
    body = _json.loads(out["content"][0]["text"])
    assert "OSError" in body["error"]


# -- memory_remember writes-delta safety net --------------------------------


def test_memory_remember_includes_writes_delta(monkeypatch, tmp_path):
    """The MCP server's memory_remember must report node/edge deltas measured
    against the store, so a sub-agent that hallucinates success is detectable.
    """
    import asyncio
    import sys

    from memory_graph import server as srv
    from memory_graph.embed import FakeEmbedder

    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))
    srv._store = None
    srv._store_root = None
    monkeypatch.setattr(srv, "_make_embedder", lambda: FakeEmbedder(dim=32))

    import memory_graph.orchestration.remember  # noqa: F401

    remember_mod = sys.modules["memory_graph.orchestration.remember"]

    # First subtest: sub-agent claims success but doesn't actually write.
    async def lying_sub_agent(**kwargs):
        return _fake_result("Wrote 9 notes successfully!")

    monkeypatch.setattr(remember_mod, "run_subagent", lying_sub_agent)
    result = asyncio.run(srv.memory_remember(dump="anything"))
    assert result["writes"]["nodes_written"] == 0
    assert result["writes"]["edges_written"] == 0
    assert "warning" in result
    assert "hallucinated" in result["warning"] or "no changes" in result["warning"]


def test_memory_remember_no_warning_when_writes_actually_happen(monkeypatch, tmp_path):
    """Counterpart: if the sub-agent *did* write, the response should NOT carry
    the warning."""
    import asyncio
    import sys

    from memory_graph import server as srv
    from memory_graph.embed import FakeEmbedder

    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))
    srv._store = None
    srv._store_root = None
    monkeypatch.setattr(srv, "_make_embedder", lambda: FakeEmbedder(dim=32))

    import memory_graph.orchestration.remember  # noqa: F401

    remember_mod = sys.modules["memory_graph.orchestration.remember"]

    # The fake sub-agent actually writes a node via the store passed to it.
    async def writing_sub_agent(**kwargs):
        store = kwargs["store"]
        store.capture(title="t", summary="s", body="b", kind="capture")
        return _fake_result("Wrote 1 note.")

    monkeypatch.setattr(remember_mod, "run_subagent", writing_sub_agent)
    result = asyncio.run(srv.memory_remember(dump="anything"))
    assert result["writes"]["nodes_written"] == 1
    assert "warning" not in result


# -- SubAgentError surfaced via the MCP tool layer --------------------------


def test_memory_remember_surfaces_subagent_error(monkeypatch, tmp_path):
    """When the sub-agent reports is_error=True, run_subagent must raise a
    SubAgentError; the MCP tool must catch that and return an `error` field
    instead of pretending success with an empty synthesis."""
    import asyncio
    import sys

    from memory_graph import server as srv
    from memory_graph.embed import FakeEmbedder
    from memory_graph.orchestration.runner import SubAgentError

    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))
    srv._store = None
    srv._store_root = None
    monkeypatch.setattr(srv, "_make_embedder", lambda: FakeEmbedder(dim=32))

    import memory_graph.orchestration.remember  # noqa: F401
    remember_mod = sys.modules["memory_graph.orchestration.remember"]

    async def failing_sub_agent(**kwargs):
        raise SubAgentError(
            "sub-agent failed (stop_reason='max_turns'): []",
            stop_reason="max_turns",
            errors=[],
        )

    monkeypatch.setattr(remember_mod, "run_subagent", failing_sub_agent)
    result = asyncio.run(srv.memory_remember(dump="anything"))
    assert "error" in result
    assert "max_turns" in result["error"] or result["stop_reason"] == "max_turns"
    assert "synthesis" not in result  # we don't pretend success


# -- async-from-event-loop regression ---------------------------------------


def _fake_result(text: str):
    from memory_graph.orchestration.runner import SubAgentResult
    return SubAgentResult(
        text=text, usage={}, model_usage={},
        total_cost_usd=0.0, stop_reason="end_turn",
    )


def test_orchestration_tools_are_awaitable_from_running_loop(s: Store, monkeypatch):
    """Regression: FastMCP runs tool handlers inside its event loop, so the
    orchestration helpers must be async (or already in a thread). A previous
    version used asyncio.run() inside the tool, which crashed with
    'asyncio.run() cannot be called from a running event loop'.
    """
    import asyncio

    # Stub the actual sub-agent runner. The orchestration modules import
    # `run_subagent` by name, so we patch each module's local reference.
    #
    # Caveat: `memory_graph.orchestration` re-exports the function
    # `remember` (etc.), which shadows the same-named submodule on
    # attribute lookup, defeating `import ... as`. Grab the module via
    # sys.modules instead.
    import sys

    import memory_graph.orchestration.compact  # ensure submodule loaded
    import memory_graph.orchestration.remember  # noqa: F401
    import memory_graph.orchestration.retrieve  # noqa: F401

    submods = [
        sys.modules[f"memory_graph.orchestration.{n}"]
        for n in ("remember", "retrieve", "compact")
    ]

    async def fake_run_subagent(**kwargs):
        return _fake_result(f"stub synthesis for task={kwargs.get('task')}")

    for mod in submods:
        monkeypatch.setattr(mod, "run_subagent", fake_run_subagent)

    from memory_graph.orchestration import compact, remember, retrieve

    async def exercise():
        # All three orchestration helpers must be awaitable; awaiting them
        # inside a running loop must not raise.
        r1 = await remember("anything", store=s)
        r2 = await retrieve("anything", store=s)
        r3 = await compact(s, scope="recent")
        return r1, r2, r3

    r1, r2, r3 = asyncio.run(exercise())
    assert "remember" in r1.text
    assert "retrieve" in r2.text
    assert "compact" in r3.text


def test_server_tools_awaitable_from_running_loop(monkeypatch, tmp_path):
    """Regression: the MCP server's three smart tools must be coroutines so
    FastMCP can await them.
    """
    import asyncio

    from memory_graph import server as srv
    from memory_graph.embed import FakeEmbedder

    # Reset and inject FakeEmbedder so we don't load the real model.
    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))
    srv._store = None
    srv._store_root = None
    monkeypatch.setattr(srv, "_make_embedder", lambda: FakeEmbedder(dim=32))

    # Stub the runner where it's used — see the comment in the previous test
    # about the submodule-vs-re-export shadowing.
    import sys

    import memory_graph.orchestration.remember  # noqa: F401

    remember_mod = sys.modules["memory_graph.orchestration.remember"]

    async def fake_run_subagent(**kwargs):
        return _fake_result("ack")

    monkeypatch.setattr(remember_mod, "run_subagent", fake_run_subagent)

    async def exercise():
        # @mcp.tool() leaves the original function in the module namespace
        # (the Tool object lives inside the registry, not as a `.fn` attr).
        return await srv.memory_remember(dump="some session dump")

    result = asyncio.run(exercise())
    assert isinstance(result, dict)
    assert result.get("synthesis") == "ack"
    # New: response carries sub-agent observability data.
    assert "sub_agent" in result
    assert "tokens" in result["sub_agent"]


# -- end-to-end (opt-in) ----------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="set CLAUDE_CODE_OAUTH_TOKEN to run a real sub-agent end-to-end",
)
def test_remember_end_to_end(s: Store):
    from memory_graph.orchestration import remember_sync

    result = remember_sync(
        "Today we tried cursor-based pagination on /ingest and it cut "
        "p95 latency from 800ms to 90ms at 5k req/s. We decided to keep "
        "it for new endpoints.",
        store=s,
    )
    assert hasattr(result, "text") and len(result.text) > 0
    # At least one note should have landed.
    assert s.status()["total_nodes"] >= 1
