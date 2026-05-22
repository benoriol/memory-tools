"""FastMCP server exposing 5 memory tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from memory_recall.embed import Embedder, LocalEmbedder
from memory_recall.storage.files import store_root
from memory_recall.store import Store
from memory_recall.subagent import expand_for_capture, expand_for_search

mcp = FastMCP("memory-recall")

_embedder: Embedder | None = None
_store: Store | None = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedder()
    return _embedder


def _get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(store_root(), _get_embedder())
    return _store


def _note_brief(note, score: float | None = None, matched_view: str | None = None) -> dict[str, Any]:
    out = {
        "id": note.id,
        "title": note.title,
        "summary": note.summary,
        "tags": note.tags,
        "created_at": note.created_at,
    }
    if score is not None:
        out["score"] = round(score, 4)
    if matched_view is not None:
        out["matched_view"] = matched_view
    return out


@mcp.tool()
async def memory_capture(content: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Save a memory for later recall.

    `content` is open-ended raw text: a finding, a decision, an
    architectural fact, a bug write-up, a snippet from a teammate's
    message — whatever you'd want to retrieve later. The sub-agent
    parses it into a structured note with a title, summary, keywords,
    paraphrases, and tags, embeds each retrieval view, and stores it.

    Returns the saved note's id + summary + the views that were
    indexed (so you can sanity-check what will be searchable).

    `tags` are optional extras that get merged with sub-agent-suggested
    tags.
    """
    expanded = await expand_for_capture(content)
    store = _get_store()
    note = store.capture(
        content,
        title=expanded["title"],
        summary=expanded["summary"],
        keywords=expanded["keywords"],
        paraphrases=expanded["paraphrases"],
        tags=list({*expanded["tags"], *(tags or [])}),
    )
    return {
        "id": note.id,
        "title": note.title,
        "summary": note.summary,
        "tags": note.tags,
        "views": {
            "summary": expanded["summary"],
            "keywords": expanded["keywords"],
            "paraphrases": expanded["paraphrases"],
        },
    }


@mcp.tool()
async def memory_retrieve_candidates(query: str, k: int = 10) -> dict[str, Any]:
    """STEP 1 of a two-step recall. Get candidate memories given an
    open-ended query.

    Recall is a two-step procedure:

      1. Call `memory_retrieve_candidates(query)`. You get back a list
         of candidate memories — id + title + summary + score + the
         single phrase that matched. NO full body text is returned.
      2. Read the summaries, decide which candidate(s) actually answer
         your question, and call `memory_get(ids=[...])` once with
         all chosen ids — it accepts a batch. Often 0-2 candidates
         need step 2.

    The `query` is open-ended. You can pass:
      - a verbatim question ("which class handles outbound retries?")
      - a task description ("I need to add a new metric to the
        telemetry buffer")
      - a bug report ("the paginator is returning empty pages for
        page 1")
      - an error message
      - a half-formed thought

    The sub-agent will parse it, generate canonical keywords and
    paraphrases, embed each, and rank notes by max-pool cosine
    similarity. The keywords/paraphrases used are returned in the
    `expanded` field so you can see what was actually searched.

    `k` is the number of candidates to return (default 10). The
    cost of larger k is small — bodies aren't included.
    """
    expanded = await expand_for_search(query)
    store = _get_store()
    hits = store.search(expanded["query_views"], k=k)
    return {
        "query": query,
        "expanded": {
            "keywords": expanded["keywords"],
            "paraphrases": expanded["paraphrases"],
        },
        "results": [_note_brief(n, s, mv) for (n, s, mv) in hits],
    }


@mcp.tool()
def memory_get(ids: list[str]) -> list[dict[str, Any] | None]:
    """STEP 2 of a two-step recall. Fetch the full bodies of one or
    more memories in a single call.

    `ids` is a list of note ids from `memory_retrieve_candidates`.
    Returns a list of the same length and order; each element is the
    note's title, summary, full body text, tags, and every indexed
    retrieval view, or `null` if that id doesn't exist.

    **Always batch.** If two or three candidate summaries look
    relevant, pass all their ids in one call rather than making
    sequential `memory_get` calls — one MCP round-trip is much
    cheaper than several. Pass a single-element list when only one
    body is needed.

    Don't call this on every candidate by default — most queries
    only need step 1's summaries.
    """
    store = _get_store()
    out: list[dict[str, Any] | None] = []
    for nid in ids:
        note = store.get(nid)
        if note is None:
            out.append(None)
            continue
        views = store.get_views(nid)
        out.append({
            **note.to_dict(),
            "views": [
                {"kind": v.view_kind, "text": v.view_text}
                for v in views
            ],
        })
    return out


@mcp.tool()
def memory_list(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Browse all memories, newest first. Pagination via `limit` /
    `offset`. Returns summaries only (id, title, summary, tags). Use
    when you want to see what's in memory without a specific query —
    e.g. orienting yourself at the start of a session.
    """
    store = _get_store()
    return [_note_brief(n) for n in store.list_notes(limit=limit, offset=offset)]


@mcp.tool()
def memory_status() -> dict[str, Any]:
    """Memory store stats: note count, embedding model, embedding dim,
    last-activity timestamp. Cheap; useful as a session-start sanity
    check.
    """
    return _get_store().status()
