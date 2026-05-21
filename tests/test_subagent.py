"""Sub-agent JSON parsing + plumbing tests."""

from __future__ import annotations

import pytest

from memory_recall import subagent
from memory_recall.subagent import _extract_json, expand_for_capture, expand_for_search


def test_extract_plain_json() -> None:
    data = _extract_json('{"a": 1, "b": "x"}')
    assert data == {"a": 1, "b": "x"}


def test_extract_json_in_fenced_block() -> None:
    text = "Here is the answer:\n```json\n{\"summary\": \"hi\"}\n```\nThanks."
    data = _extract_json(text)
    assert data == {"summary": "hi"}


def test_extract_json_with_prose() -> None:
    text = "Sure thing! Output: {\"k\": [1,2,3]}\nEnd."
    data = _extract_json(text)
    assert data == {"k": [1, 2, 3]}


def test_extract_json_nested_braces() -> None:
    text = 'noise {"outer": {"inner": "v"}, "tail": 1} more noise'
    data = _extract_json(text)
    assert data == {"outer": {"inner": "v"}, "tail": 1}


def test_extract_json_missing_raises() -> None:
    with pytest.raises(ValueError):
        _extract_json("no json here")


async def test_expand_for_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_query(prompt: str, *, model: str | None) -> str:
        assert "raw note text" in prompt
        return '{"title": "T", "summary": "S", "keywords": ["k1","k2"], "paraphrases": ["p1?"], "tags": ["x"]}'

    monkeypatch.setattr(subagent, "_run_query", fake_run_query)
    out = await expand_for_capture("raw note text")
    assert out["title"] == "T"
    assert out["summary"] == "S"
    assert out["keywords"] == ["k1", "k2"]
    assert out["paraphrases"] == ["p1?"]
    assert out["tags"] == ["x"]


async def test_expand_for_search_includes_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_query(prompt: str, *, model: str | None) -> str:
        return '```json\n{"keywords":["alpha","beta"],"paraphrases":["What is X?"]}\n```'

    monkeypatch.setattr(subagent, "_run_query", fake_run_query)
    out = await expand_for_search("how do we Y?")
    assert "how do we Y?" in out["query_views"]
    assert "alpha" in out["query_views"]
    assert "What is X?" in out["query_views"]


async def test_expand_capture_fallback_on_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_query(prompt: str, *, model: str | None) -> str:
        return '{}'

    monkeypatch.setattr(subagent, "_run_query", fake_run_query)
    out = await expand_for_capture("first line\nsecond line")
    # Empty fields should default to non-empty fallbacks for title/summary.
    assert out["title"]
    assert out["summary"]
    assert out["keywords"] == []
    assert out["paraphrases"] == []


async def test_expand_capture_propagates_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_query(prompt: str, *, model: str | None) -> str:
        return "no json at all"

    monkeypatch.setattr(subagent, "_run_query", fake_run_query)
    with pytest.raises(ValueError):
        await expand_for_capture("anything")
