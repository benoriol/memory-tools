"""MCP tool registration and roundtrip."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_recall import server as server_module
from memory_recall.embed import DeterministicFakeEmbedder
from memory_recall.store import Store


async def test_list_tools_has_5() -> None:
    tools = await server_module.mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "memory_capture",
        "memory_retrieve_candidates",
        "memory_get",
        "memory_list",
        "memory_status",
    }


async def test_capture_and_status_roundtrip(
    store_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(store_root, DeterministicFakeEmbedder())
    monkeypatch.setattr(server_module, "_get_store", lambda: store)
    monkeypatch.setattr(server_module, "_get_embedder", lambda: store.embedder)

    async def fake_capture(content: str, *, model=None):
        return {
            "title": "T",
            "summary": "S",
            "keywords": ["k1"],
            "paraphrases": ["p1?"],
            "tags": [],
        }

    monkeypatch.setattr(server_module, "expand_for_capture", fake_capture)

    result = await server_module.mcp.call_tool(
        "memory_capture", {"content": "hello"}
    )
    payload = _parse_tool_result(result)
    assert payload["title"] == "T"
    nid = payload["id"]

    listed = await server_module.mcp.call_tool("memory_list", {})
    list_payload = _parse_tool_result(listed)
    assert any(item["id"] == nid for item in list_payload)

    got = await server_module.mcp.call_tool("memory_get", {"id": nid})
    got_payload = _parse_tool_result(got)
    assert got_payload["id"] == nid
    kinds = sorted(v["kind"] for v in got_payload["views"])
    assert kinds == ["keyword", "paraphrase", "summary"]

    status = await server_module.mcp.call_tool("memory_status", {})
    assert _parse_tool_result(status)["count"] == 1


async def test_search_tool_roundtrip(
    store_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(store_root, DeterministicFakeEmbedder())
    monkeypatch.setattr(server_module, "_get_store", lambda: store)

    async def fake_capture(content: str, *, model=None):
        return {
            "title": "T", "summary": content, "keywords": [content],
            "paraphrases": [content], "tags": [],
        }

    async def fake_search(query: str, *, model=None):
        return {"keywords": [query], "paraphrases": [query], "query_views": [query]}

    monkeypatch.setattr(server_module, "expand_for_capture", fake_capture)
    monkeypatch.setattr(server_module, "expand_for_search", fake_search)

    await server_module.mcp.call_tool(
        "memory_capture", {"content": "unique-needle-text"}
    )
    out = await server_module.mcp.call_tool(
        "memory_retrieve_candidates", {"query": "unique-needle-text", "k": 5}
    )
    payload = _parse_tool_result(out)
    assert len(payload["results"]) == 1
    assert payload["results"][0]["score"] > 0.99


def _parse_tool_result(result):
    # FastMCP returns (content_list, structured_content) or similar; handle both.
    if isinstance(result, tuple):
        content, structured = result
        if structured is not None:
            # Tool returning a list comes through as {"result": [...]}
            if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
                return structured["result"]
            return structured
        return json.loads(content[0].text)
    return result
