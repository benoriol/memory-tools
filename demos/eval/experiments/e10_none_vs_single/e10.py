"""e10 — NONE vs SINGLE on cross-session bug recall.

The most basic Q1 test. Same corpus as e01 (30 buggy Python modules,
ground-truth held in this harness). Two arms differ only by prompt:

- NONE: phase-1 prompt says "investigate" — no mention of notes.
        Phase-2 prompt says "the prior session left no notes."
- SINGLE: phase-1 prompt says "maintain NOTES.md".
          Phase-2 prompt says "your prior session left NOTES.md".

Both arms have Read/Write/Bash/Glob/Grep. No MCP. Files persist
between phases. Each phase = fresh query() call.

Pass: both arms >= 28/30 accuracy AND SINGLE p2 cost <= 0.5 * NONE p2.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

RAM_BYTES_CAP = 32 * 1024 ** 3
CPU_CORES_CAP = 64


def _apply_limits() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (RAM_BYTES_CAP, RAM_BYTES_CAP))
    except (ValueError, OSError) as exc:
        print(f"[limits] RLIMIT_AS not applied: {exc}", file=sys.stderr)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(cpus[:CPU_CORES_CAP]))
    except (AttributeError, OSError) as exc:
        print(f"[limits] sched_setaffinity not applied: {exc}", file=sys.stderr)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


_apply_limits()


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE
WORK_BASE = Path("/tmp/lab-bench")


def _load_bug_specs() -> list[dict[str, Any]]:
    """Import BUG_SPECS from e01.py without running its main."""
    e01_path = HERE.parent / "e01_realistic_baseline" / "e01.py"
    spec = importlib.util.spec_from_file_location("e01_specs", e01_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BUG_SPECS


BUG_SPECS = _load_bug_specs()
assert len(BUG_SPECS) == 30


def _generate_codebase(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for i, spec in enumerate(BUG_SPECS):
        mod_name = f"module_{i:02d}"
        header = f'"""{ spec["domain"] } (module {mod_name})."""\n\n'
        body = header + spec["code"]
        (workdir / f"{mod_name}.py").write_text(body)
    (workdir / "README.md").write_text(
        "# Dataflow demo project\n\n"
        "30 small modules. Each contains a single defect.\n"
    )


PHASE1_PROMPT_NONE = """\
You are reviewing the small Python codebase in this directory. There
are 30 modules (`module_00.py` through `module_29.py`). Each module's
class/function body contains exactly ONE planted defect.

YOUR TASK: read every module and identify the defect in each.

Do not assume any particular workflow — proceed however you find
natural.
"""


PHASE1_PROMPT_SINGLE = """\
You are reviewing the small Python codebase in this directory. There
are 30 modules (`module_00.py` through `module_29.py`). Each module's
class/function body contains exactly ONE planted defect.

YOUR TASK: read every module and identify the defect in each.

A different agent will be asked diagnostic questions about this code
tomorrow. They will not see your reading history. The source files
will still be on disk but they will have no record of your
investigation.

LEAVE NOTES. Maintain a single file called `NOTES.md` in this
directory. After investigating each module, append a section like:

```
## module_NN
**Bug**: <one-line summary of the bug type>
**Detail**: <a sentence or two with the specific symptom>
```

That `NOTES.md` is the ONLY way your work persists into tomorrow. Do
not write any other notes files; do not write code; just produce
`NOTES.md`.
"""


PHASE2_PROMPT_NONE = """\
Answer the following diagnostic questions about the codebase in this
directory.

There are 30 modules (`module_00.py` through `module_29.py`) on disk.
A prior agent investigated this codebase but left you no notes — you
will need to read modules yourself.

Output your answers in EXACTLY this format on the last 30 lines:

Q01: module_NN — <one-line description of the bug>
Q02: module_NN — <one-line description of the bug>
...
Q30: module_NN — <one-line description of the bug>

Use the EXACT module name (module_00, module_07, ...) and describe
the bug in plain language.

Questions:
{questions}
"""


PHASE2_PROMPT_SINGLE = """\
Answer the following diagnostic questions about the codebase in this
directory.

There are 30 modules (`module_00.py` through `module_29.py`) on disk.
A prior agent already investigated this codebase and left their notes
in `NOTES.md`. READ NOTES.md ONCE — it contains one section per module
with the bug type and a brief detail. Use those notes to answer.

Only read individual source modules if `NOTES.md` is unclear or
incomplete for a specific question.

Output your answers in EXACTLY this format on the last 30 lines:

Q01: module_NN — <one-line description of the bug>
Q02: module_NN — <one-line description of the bug>
...
Q30: module_NN — <one-line description of the bug>

Use the EXACT module name (module_00, module_07, ...) and describe
the bug in plain language.

Questions:
{questions}
"""


async def run_phase(
    prompt: str,
    workdir: Path,
    *,
    max_turns: int = 90,
) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=["Read", "Bash", "Glob", "Grep", "Write", "Edit"],
        mcp_servers={},
        max_turns=max_turns,
    )

    text_chunks: list[str] = []
    tool_calls: list[str] = []
    last_result = None
    t0 = time.monotonic()
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                t = getattr(block, "text", None)
                if t:
                    text_chunks.append(t)
                tn = getattr(block, "name", None)
                if tn:
                    tool_calls.append(tn)
        elif isinstance(msg, ResultMessage):
            last_result = msg
    usage = dict(getattr(last_result, "usage", None) or {}) if last_result else {}
    cost = getattr(last_result, "total_cost_usd", None) if last_result else None
    return {
        "text": "\n".join(text_chunks).strip(),
        "usage": usage,
        "cost_usd": cost,
        "seconds": round(time.monotonic() - t0, 1),
        "tool_calls": tool_calls,
    }


def grade(text: str, truth: list[dict]) -> dict[str, Any]:
    import re

    pattern_map: dict[int, str] = {}
    for i in range(len(truth)):
        m = re.search(rf"Q{i + 1:02d}\s*:\s*(.+)", text or "")
        pattern_map[i + 1] = m.group(1).strip() if m else ""

    per_q: dict[int, dict[str, Any]] = {}
    hits = 0
    for i, spec in enumerate(truth):
        got = pattern_map.get(i + 1, "").lower()
        expected_module = f"module_{i:02d}"
        keyword_hit = any(kw.lower() in got for kw in spec["keywords"])
        module_hit = expected_module in got
        ok = module_hit and keyword_hit
        if ok:
            hits += 1
        per_q[i + 1] = {
            "id": spec["id"],
            "expected_module": expected_module,
            "raw": pattern_map.get(i + 1, ""),
            "module_hit": module_hit,
            "keyword_hit": keyword_hit,
            "ok": ok,
        }
    return {
        "score": round(hits / len(truth), 3),
        "hits": hits,
        "total": len(truth),
        "per_question": per_q,
    }


def _inventory_files(workdir: Path) -> dict[str, Any]:
    """Catalog non-source files the agent left in phase 1."""
    src_names = {f"module_{i:02d}.py" for i in range(len(BUG_SPECS))}
    src_names.add("README.md")
    out: list[dict[str, Any]] = []
    for path in sorted(workdir.iterdir()):
        if path.name in src_names:
            continue
        if path.is_file():
            out.append({
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "lines": len(path.read_text(errors="replace").splitlines()),
            })
        elif path.is_dir():
            out.append({"name": path.name + "/", "size_bytes": -1, "lines": -1})
    notes_md = workdir / "NOTES.md"
    return {
        "files": out,
        "notes_md_size": notes_md.stat().st_size if notes_md.exists() else 0,
    }


async def run_arm(arm: str) -> dict[str, Any]:
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = WORK_BASE / f"e10-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    _generate_codebase(workdir)

    if arm == "none":
        p1_prompt = PHASE1_PROMPT_NONE
        p2_prompt_tmpl = PHASE2_PROMPT_NONE
    elif arm == "single":
        p1_prompt = PHASE1_PROMPT_SINGLE
        p2_prompt_tmpl = PHASE2_PROMPT_SINGLE
    else:
        raise ValueError(arm)

    print(f"=== e10 ARM: {arm} ===")
    print(f"  workdir: {workdir}")
    print("  phase 1 (investigate) ... ", end="", flush=True)
    p1 = await run_phase(p1_prompt, workdir, max_turns=90)
    inv = _inventory_files(workdir)
    tool_counts_p1: dict[str, int] = {}
    for t in p1["tool_calls"]:
        tool_counts_p1[t] = tool_counts_p1.get(t, 0) + 1
    print(f"{p1['seconds']}s  cost=${p1['cost_usd'] or 0:.4f}  "
          f"non_src_files={len(inv['files'])}  NOTES.md={inv['notes_md_size']}B")
    print(f"  phase1 tool calls: {tool_counts_p1}")

    questions = "\n".join(f"Q{i + 1:02d}: {s['question']}" for i, s in enumerate(BUG_SPECS))
    print("  phase 2 (diagnose) ... ", end="", flush=True)
    p2 = await run_phase(
        p2_prompt_tmpl.format(questions=questions),
        workdir,
        max_turns=60,
    )
    tool_counts_p2: dict[str, int] = {}
    for t in p2["tool_calls"]:
        tool_counts_p2[t] = tool_counts_p2.get(t, 0) + 1
    print(f"{p2['seconds']}s  cost=${p2['cost_usd'] or 0:.4f}")
    print(f"  phase2 tool calls: {tool_counts_p2}")

    sc = grade(p2["text"], BUG_SPECS)
    print(f"  score: {sc['hits']}/{sc['total']}  ({sc['score']:.2%})")

    return {
        "arm": arm,
        "score": sc,
        "phase1": {k: v for k, v in p1.items() if k != "text"},
        "phase2": {k: v for k, v in p2.items() if k != "text"},
        "phase2_text_tail": "\n".join(p2["text"].splitlines()[-32:]),
        "phase1_inventory": inv,
        "tool_counts_phase1": tool_counts_p1,
        "tool_counts_phase2": tool_counts_p2,
        "phase1_cost_usd": p1.get("cost_usd") or 0,
        "phase2_cost_usd": p2.get("cost_usd") or 0,
        "total_cost_usd": (p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0),
        "total_seconds": round(p1["seconds"] + p2["seconds"], 1),
    }


async def main_async() -> int:
    print("=" * 64)
    print("e10: NONE vs SINGLE on cross-session bug recall")
    print("=" * 64)
    none_arm = await run_arm("none")
    single_arm = await run_arm("single")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "e10_results.json").write_text(
        json.dumps({"none": none_arm, "single": single_arm}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  NONE    {none_arm['score']['hits']}/30  "
          f"total=${none_arm['total_cost_usd']:.4f} ({none_arm['total_seconds']}s)  "
          f"p2=${none_arm['phase2_cost_usd']:.4f}")
    print(f"  SINGLE  {single_arm['score']['hits']}/30  "
          f"total=${single_arm['total_cost_usd']:.4f} ({single_arm['total_seconds']}s)  "
          f"p2=${single_arm['phase2_cost_usd']:.4f}  "
          f"NOTES.md={single_arm['phase1_inventory']['notes_md_size']}B")
    acc_ok = none_arm["score"]["hits"] >= 28 and single_arm["score"]["hits"] >= 28
    cost_ok = single_arm["phase2_cost_usd"] <= 0.5 * none_arm["phase2_cost_usd"]
    verdict = "PASS" if (acc_ok and cost_ok) else "FAIL"
    print(f"  verdict: {verdict}  (accuracy_pass={acc_ok}, cost_pass={cost_ok})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
