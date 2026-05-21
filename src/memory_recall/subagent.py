"""Sub-agent calls that expand notes/queries into multi-vector views."""

from __future__ import annotations

import json
import os
import re
from importlib import resources
from typing import Any

# Sonnet 4.6 with extended thinking disabled. Chosen empirically in
# e25 / e25b: best recall@1 (92%) at ~3.5s/search call. Haiku 4.5 is
# faster (~2.7s) but loses 18pp recall@1 on the same task. Override
# only via the MEMORY_RECALL_SUBAGENT_MODEL env var.
DEFAULT_MODEL = "claude-sonnet-4-6"
_PROMPT_PKG = "memory_recall.prompts"


def _load_prompt(name: str) -> str:
    return resources.files(_PROMPT_PKG).joinpath(name).read_text()


def _resolved_model(model: str | None) -> str:
    return model or os.environ.get("MEMORY_RECALL_SUBAGENT_MODEL") or DEFAULT_MODEL


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of `text`, tolerating prose + markdown fences."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("{")
        if start == -1:
            raise ValueError(f"no JSON object found in sub-agent response: {text!r}")
        depth = 0
        end = -1
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        if end == -1:
            raise ValueError(f"unbalanced JSON in sub-agent response: {text!r}")
        candidate = text[start:end]
    return json.loads(candidate)


async def _run_query(prompt: str, *, model: str | None) -> str:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        query,
    )

    # Thinking explicitly disabled: with effort="low" Haiku 4.5 still
    # spends ~5.7s/call on hidden thinking tokens (confirmed via probe);
    # Sonnet 4.6 also benefits slightly. The sub-agent task is mechanical
    # canonicalization — thinking helps neither model on this workload.
    options = ClaudeAgentOptions(
        model=_resolved_model(model),
        thinking={"type": "disabled"},
        max_thinking_tokens=0,
        permission_mode="bypassPermissions",
        allowed_tools=[],
        mcp_servers={},
        max_turns=1,
    )
    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                t = getattr(block, "text", None)
                if t:
                    chunks.append(t)
    return "\n".join(chunks).strip()


async def expand_for_capture(content: str, *, model: str | None = None) -> dict[str, Any]:
    """Return {title, summary, keywords, paraphrases, tags} for a raw note."""
    prompt = _load_prompt("capture.md").replace("{content}", content)
    raw = await _run_query(prompt, model=model)
    data = _extract_json(raw)
    return {
        "title": str(data.get("title", "")).strip() or content.splitlines()[0][:80],
        "summary": str(data.get("summary", "")).strip() or content[:200],
        "keywords": [str(x).strip() for x in data.get("keywords", []) if str(x).strip()],
        "paraphrases": [
            str(x).strip() for x in data.get("paraphrases", []) if str(x).strip()
        ],
        "tags": [str(x).strip() for x in data.get("tags", []) if str(x).strip()],
    }


async def expand_for_search(query: str, *, model: str | None = None) -> dict[str, Any]:
    """Return {keywords, paraphrases, query_views} for a raw query."""
    prompt = _load_prompt("search.md").replace("{query}", query)
    raw = await _run_query(prompt, model=model)
    data = _extract_json(raw)
    keywords = [str(x).strip() for x in data.get("keywords", []) if str(x).strip()]
    paraphrases = [str(x).strip() for x in data.get("paraphrases", []) if str(x).strip()]
    views = [query.strip(), *keywords, *paraphrases]
    return {
        "keywords": keywords,
        "paraphrases": paraphrases,
        "query_views": views,
    }
