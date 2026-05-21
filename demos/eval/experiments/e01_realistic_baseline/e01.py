"""e01 — Realistic baseline replication.

See README.md for design. Two phases, two arms, files preserved
between phases. Each phase = fresh query() call. The no_memory arm
has Write/Edit so it can keep its own scratch notes (realistic
fallback). The with_memory arm additionally has the memory_graph
tools.

Task: 30 synthetic Python modules, each with one planted bug.
Phase 1: investigate every module, identify each bug.
Phase 2: 30 paraphrased diagnostic questions; agent must name the
module and bug.

Pass: both arms >= 28/30, with_memory phase-2 cost <= 0.5 *
no_memory phase-2 cost.
"""

from __future__ import annotations

import asyncio
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Resource limits — apply before any heavyweight imports.
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


REPO_ROOT = Path(__file__).resolve().parents[4]
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"
RESULTS_DIR = Path(__file__).resolve().parent
WORK_BASE = Path("/tmp/lab-bench")


# Each spec gives the bug code (with its bug) and a paraphrased question
# whose phrasing does NOT match identifiers in the code, so phase-2 can't
# just grep the question text.
BUG_SPECS: list[dict[str, Any]] = [
    {
        "id": "off_by_one_page",
        "domain": "Paginator for catalog browser",
        "code": '''class Paginator:
    def __init__(self, items, page_size):
        self.items = items
        self.page_size = page_size

    def get_page(self, n):
        # Returns items for page n (1-indexed).
        start = n * self.page_size
        end = start + self.page_size
        return self.items[start:end]
''',
        "question": "Which module mis-indexes the first page so that items 0 through page_size-1 are skipped?",
        "keywords": ["off-by-one", "off by one", "n-1", "1-indexed", "first page", "skip"],
    },
    {
        "id": "retry_off_by_one",
        "domain": "Retry policy for failed jobs",
        "code": '''class RetryPolicy:
    MAX_ATTEMPTS = 3

    def __init__(self):
        self.attempts = 0

    def should_retry(self, last_error):
        self.attempts += 1
        return self.attempts < self.MAX_ATTEMPTS
''',
        "question": "Which module stops retrying one attempt too early?",
        "keywords": ["off-by-one", "<=", "less than", "early", "one less", "MAX_ATTEMPTS", "<"],
    },
    {
        "id": "cache_invalidate_noop",
        "domain": "In-memory cache with TTL",
        "code": '''class Cache:
    def __init__(self):
        self._store = {}

    def set(self, key, value):
        self._store[key] = value

    def get(self, key):
        return self._store.get(key)

    def invalidate(self):
        # Should drop all entries.
        keys = list(self._store.keys())
        # Forgot to actually clear.
        return len(keys)
''',
        "question": "Which module's reset/clear method silently does nothing — entries persist after the call?",
        "keywords": ["invalidate", "clear", "no-op", "noop", "doesn't clear", "does not clear", "forgot"],
    },
    {
        "id": "timeout_wrong_unit",
        "domain": "HTTP client with timeout",
        "code": '''import socket


class HttpClient:
    def __init__(self, timeout_ms):
        self.timeout_ms = timeout_ms

    def connect(self, host, port):
        s = socket.socket()
        # socket.settimeout takes seconds.
        s.settimeout(self.timeout_ms)
        s.connect((host, port))
        return s
''',
        "question": "Which module configures a network deadline 1000x larger than intended?",
        "keywords": ["unit", "ms", "second", "millisecond", "1000", "settimeout", "/1000"],
    },
    {
        "id": "mutable_default",
        "domain": "Config loader with overrides",
        "code": '''class ConfigLoader:
    def load(self, overrides={}):
        defaults = {"timeout": 30, "retries": 3}
        defaults.update(overrides)
        return defaults
''',
        "question": "Which module has a function whose default argument is a shared mutable value?",
        "keywords": ["mutable default", "mutable", "default", "argument", "shared", "{}", "[]"],
    },
    {
        "id": "integer_division_mean",
        "domain": "Statistics calculator",
        "code": '''class StatsCalculator:
    def mean(self, values):
        total = sum(values)
        return total // len(values)
''',
        "question": "Which module computes an average but truncates to an integer?",
        "keywords": ["integer division", "//", "truncate", "int", "float", "mean", "average"],
    },
    {
        "id": "file_not_closed",
        "domain": "File writer with batching",
        "code": '''class FileWriter:
    def __init__(self, path):
        self.f = open(path, "w")

    def write_batch(self, lines):
        for line in lines:
            if not line:
                raise ValueError("empty")
            self.f.write(line + "\\n")
        # Forgot to flush/close on exception.
''',
        "question": "Which module leaks a file handle when an exception is raised mid-write?",
        "keywords": ["leak", "not closed", "close", "context manager", "with", "finally", "exception"],
    },
    {
        "id": "regex_partial",
        "domain": "Log line parser",
        "code": '''import re


class LogParser:
    PATTERN = re.compile(r"\\d{4}-\\d{2}-\\d{2}")

    def is_date(self, s):
        return bool(self.PATTERN.match(s))
''',
        "question": "Which module's validator accepts strings that merely begin with the expected pattern?",
        "keywords": ["anchor", "partial match", "fullmatch", "$", "^", "regex", "match", "begin"],
    },
    {
        "id": "queue_negative_index",
        "domain": "Priority queue",
        "code": '''class PriorityQueue:
    def __init__(self):
        self.items = []

    def push(self, x):
        self.items.append(x)

    def peek_last(self):
        # Returns the most recently added item.
        return self.items[len(self.items)]
''',
        "question": "Which module raises IndexError when reading the tail of a non-empty list?",
        "keywords": ["IndexError", "len", "-1", "off-by-one", "index", "tail", "last"],
    },
    {
        "id": "dict_keyerror",
        "domain": "Settings store",
        "code": '''class SettingsStore:
    def __init__(self):
        self._data = {"theme": "dark"}

    def lookup(self, key):
        return self._data[key]
''',
        "question": "Which module crashes when asked about a setting that was never written?",
        "keywords": ["KeyError", "missing", ".get", "default", "not present", "absent"],
    },
    {
        "id": "swapped_args",
        "domain": "Temperature converter",
        "code": '''class TemperatureConverter:
    def convert(self, celsius, fahrenheit):
        # Convert celsius to fahrenheit.
        return celsius * 9 / 5 + 32

    def round_trip(self, c):
        # Should go C -> F -> C.
        f = self.convert(c, 0)
        # Bug below: passes F first.
        return self.convert(f, 0)
''',
        "question": "Which module re-applies the same forward conversion when it should reverse direction?",
        "keywords": ["swap", "swapped", "argument order", "reverse", "inverse", "round_trip", "direction"],
    },
    {
        "id": "early_return_skips_cleanup",
        "domain": "Validator with error tracking",
        "code": '''class Validator:
    def __init__(self):
        self.errors = []

    def validate(self, data):
        if not data:
            return False
        if "id" not in data:
            self.errors.append("missing id")
            return False
        # Should clear errors before returning True, but never reached
        # consistently because the next line returns first:
        return True
        self.errors.clear()
''',
        "question": "Which module has unreachable cleanup code positioned after a return statement?",
        "keywords": ["unreachable", "after return", "dead code", "clear", "cleanup"],
    },
    {
        "id": "shallow_alias",
        "domain": "State snapshot helper",
        "code": '''class State:
    def __init__(self):
        self._data = {"x": 1}

    def snapshot(self):
        # Returns a snapshot of current state.
        return self._data
''',
        "question": "Which module returns a 'snapshot' that mutates when the original changes?",
        "keywords": ["copy", "alias", "reference", "shallow", "mutate", "deep", "dict.copy"],
    },
    {
        "id": "zero_division",
        "domain": "Average computer",
        "code": '''class Average:
    def compute(self, values):
        return sum(values) / len(values)
''',
        "question": "Which module raises ZeroDivisionError on an empty input list?",
        "keywords": ["ZeroDivisionError", "empty", "zero", "len(values)", "guard", "division"],
    },
    {
        "id": "tail_empty_n",
        "domain": "Bounded buffer with tail accessor",
        "code": '''class Buffer:
    def __init__(self):
        self.items = []

    def add(self, x):
        self.items.append(x)

    def tail(self, n):
        # Returns last n items.
        return self.items[-n:]
''',
        "question": "Which module's tail() returns the entire buffer when asked for zero items?",
        "keywords": ["-0", "negative zero", "[-0:]", "tail", "n=0", "zero", "slice"],
    },
    {
        "id": "tz_naive",
        "domain": "Scheduler for next-run computation",
        "code": '''from datetime import datetime, timedelta


class Scheduler:
    def __init__(self, interval_minutes):
        self.interval = timedelta(minutes=interval_minutes)

    def next_run(self):
        return datetime.now() + self.interval
''',
        "question": "Which module produces a timestamp lacking timezone information?",
        "keywords": ["timezone", "tz", "naive", "utcnow", "tzinfo", "datetime.now"],
    },
    {
        "id": "boolean_and_vs_or",
        "domain": "Permission check",
        "code": '''class PermissionCheck:
    def can_access(self, user_admin: bool, in_org: bool) -> bool:
        # User must be admin AND in the organization.
        return user_admin or in_org
''',
        "question": "Which module's access gate lets through users who satisfy only one of two required conditions?",
        "keywords": ["and", "or", "operator", "boolean", "wrong operator", "&", "|"],
    },
    {
        "id": "range_exclusive",
        "domain": "Numeric range containment",
        "code": '''class NumericRange:
    def __init__(self, lo, hi):
        self.lo = lo
        self.hi = hi

    def contains(self, x):
        # Inclusive range check.
        return self.lo <= x < self.hi
''',
        "question": "Which module's containment check excludes the upper endpoint despite documenting inclusivity?",
        "keywords": ["exclusive", "<= hi", "<=", "boundary", "endpoint", "upper", "inclusive"],
    },
    {
        "id": "eval_user_input",
        "domain": "Query expression evaluator",
        "code": '''class QueryEval:
    def evaluate(self, expression: str, context: dict):
        # Evaluate a user-provided expression.
        return eval(expression, {}, context)
''',
        "question": "Which module executes attacker-controlled strings as code?",
        "keywords": ["eval", "code injection", "RCE", "unsafe", "user input", "security", "ast.literal_eval"],
    },
    {
        "id": "concat_in_loop",
        "domain": "Large string builder",
        "code": '''class StringBuilder:
    def build(self, parts):
        out = ""
        for p in parts:
            out += p
        return out
''',
        "question": "Which module concatenates iteratively in a way that scales quadratically with input size?",
        "keywords": ["quadratic", "O(n", "concatenat", "join", "+=", "string build", "n^2", "n squared"],
    },
    {
        "id": "generator_twice",
        "domain": "Two-pass statistics over iterable",
        "code": '''class TwoPass:
    def __init__(self, items):
        self.items = items

    def stats(self):
        total = sum(self.items)
        count = sum(1 for _ in self.items)
        return total, count
''',
        "question": "Which module fails when fed a single-use generator, returning zero for one of its results?",
        "keywords": ["generator", "iterator", "consumed", "twice", "exhaust", "single-use", "list"],
    },
    {
        "id": "class_level_list",
        "domain": "Subscription manager",
        "code": '''class Subscription:
    subscribers = []

    def add(self, name):
        self.subscribers.append(name)
''',
        "question": "Which module's instances unexpectedly share state with each other?",
        "keywords": ["class-level", "class variable", "shared", "instance", "mutable", "subscribers"],
    },
    {
        "id": "isinstance_wrong_var",
        "domain": "Type-checking dispatcher",
        "code": '''class Dispatcher:
    def handle(self, payload):
        envelope = {"data": payload, "ts": 0}
        if isinstance(payload, dict):
            return envelope
        # Below is supposed to check the dict envelope, not the payload:
        if isinstance(payload, list):
            return envelope["data"]
        return None
''',
        "question": "Which module has a conditional branch that can never be true because it checks the wrong variable?",
        "keywords": ["isinstance", "wrong variable", "never true", "dead code", "envelope", "payload"],
    },
    {
        "id": "float_equality",
        "domain": "Tolerance threshold check",
        "code": '''class Threshold:
    def hit(self, x):
        # True if x has reached exactly the threshold.
        return x == 0.1
''',
        "question": "Which module uses exact equality with a floating-point literal, missing values arbitrarily close to it?",
        "keywords": ["float", "==", "equality", "epsilon", "tolerance", "math.isclose", "0.1"],
    },
    {
        "id": "race_increment",
        "domain": "Thread-safe counter",
        "code": '''class Counter:
    def __init__(self):
        self.value = 0

    def incr(self):
        # Documented thread-safe.
        self.value = self.value + 1
''',
        "question": "Which module advertises concurrency safety but performs a non-atomic read-modify-write?",
        "keywords": ["race", "atomic", "lock", "thread", "concurrent", "read-modify-write", "non-atomic"],
    },
    {
        "id": "encoding_mismatch",
        "domain": "Log writer with declared encoding",
        "code": '''class Logger:
    DECLARED_ENCODING = "utf-8"

    def __init__(self, path):
        # Open file with utf-16 even though we tell consumers utf-8.
        self.f = open(path, "w", encoding="utf-16")

    def log(self, msg):
        self.f.write(msg + "\\n")
''',
        "question": "Which module declares one byte encoding to consumers but writes a different one to disk?",
        "keywords": ["encoding", "utf-8", "utf-16", "mismatch", "declared", "different"],
    },
    {
        "id": "wrong_magnitude",
        "domain": "Session cache TTL",
        "code": '''class SessionCache:
    TTL_SECONDS = 86400000  # one hour
    # NOTE: 86400000 is ~1000 days, not one hour (3600).
''',
        "question": "Which module's TTL constant is roughly four orders of magnitude larger than the comment claims?",
        "keywords": ["TTL", "magnitude", "constant", "wrong value", "3600", "comment", "off by"],
    },
    {
        "id": "fmt_string_args",
        "domain": "Error reporter",
        "code": '''class Reporter:
    def report(self, code, label):
        # Expected: code is int, label is string.
        msg = "code=%d label=%s" % (label, code)
        return msg
''',
        "question": "Which module swaps the order of arguments passed into a printf-style format string?",
        "keywords": ["swap", "arguments", "format", "%d", "%s", "order", "wrong"],
    },
    {
        "id": "missing_default",
        "domain": "Argument parser lookup",
        "code": '''class ArgParser:
    def __init__(self):
        self._parsed = {}

    def parse(self, argv):
        for a in argv:
            k, _, v = a.partition("=")
            self._parsed[k] = v

    def get(self, key):
        # Should fall back when key absent, but raises instead.
        return self._parsed[key]
''',
        "question": "Which module's lookup interface fails hard on absent keys instead of returning a default?",
        "keywords": ["default", "KeyError", "missing", ".get", "fallback", "absent"],
    },
    {
        "id": "negative_modulo",
        "domain": "Cyclic index helper",
        "code": '''class Ring:
    def __init__(self, size):
        self.size = size

    def at(self, idx):
        # Returns idx wrapped into [0, size).
        return idx % self.size if idx >= 0 else -((-idx) % self.size)
''',
        "question": "Which module's modular wrap-around produces negative outputs for negative inputs, breaking its stated range?",
        "keywords": ["modulo", "negative", "wrap", "range", "[0,", "modular", "negative result"],
    },
]

assert len(BUG_SPECS) == 30, f"expected 30 specs, got {len(BUG_SPECS)}"


def _generate_codebase(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for i, spec in enumerate(BUG_SPECS):
        mod_name = f"module_{i:02d}"
        header = f'"""{ spec["domain"] } (module {mod_name})."""\n\n'
        body = header + spec["code"]
        (workdir / f"{mod_name}.py").write_text(body)
    (workdir / "README.md").write_text(
        "# Dataflow demo project\n\n"
        "30 small modules forming a fictional dataflow project. Each module\n"
        "contains a single component with one notable defect — a future\n"
        "code-review pass should identify it.\n"
    )


PHASE1_PROMPT = """\
You are reviewing the small Python codebase in this directory. There
are 30 modules (`module_00.py` through `module_29.py`). EACH module's
class/function body contains exactly ONE planted defect — an off-by-one,
a wrong default, a missing null check, a swapped argument, an
unreachable branch, a wrong unit, etc.

YOUR TASK: read every module and IDENTIFY each bug. A different agent
tomorrow will be asked specific diagnostic questions — they will NOT
see your reading history. The files will still be on disk but they
will have no record of your investigation.

LEAVE NOTES so the next agent can answer. You may use any tools you
have:
- If `mcp__memory-graph__*` tools are available, prefer
  `memory_capture_batch` — write one note per module, including the
  module name, the bug type in plain language, and the specific symptom.
- If those tools are NOT available, write your notes to disk (the
  next agent will be able to read whatever files you create).

Read all 30 modules carefully. For each one:
  (a) name the module (module_NN),
  (b) name the bug type or symptom in plain language.
"""


PHASE2_PROMPT = """\
Answer the following diagnostic questions about the codebase in this
directory.

There are 30 modules (`module_00.py` through `module_29.py`) still on
disk. A prior agent already investigated this codebase — their notes
are either in the memory graph (if you have `mcp__memory-graph__*`
tools) or in files they wrote to the working directory (if not).

YOU SHOULD CONSULT THE PRIOR AGENT'S NOTES FIRST before falling back
to re-reading source files. If you have memory tools, call
`memory_search` or `memory_retrieve` with each question. If you don't,
`ls` the directory and read whatever notes file the prior agent wrote.

Output your answers in EXACTLY this format on the last 30 lines:

Q01: module_NN — <one-line description of the bug>
Q02: module_NN — <one-line description of the bug>
...
Q30: module_NN — <one-line description of the bug>

Use the EXACT module name (module_00, module_07, etc.) and describe
the bug in plain language (e.g., "off-by-one in retry attempt count").

Questions:
{questions}
"""


async def run_phase(
    prompt: str,
    workdir: Path,
    *,
    with_memory: bool,
    max_turns: int = 90,
) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    allowed = ["Read", "Bash", "Glob", "Grep", "Write", "Edit"]
    mcp_servers: dict[str, Any] = {}
    if with_memory:
        allowed += [
            "mcp__memory-graph__memory_remember",
            "mcp__memory-graph__memory_retrieve",
            "mcp__memory-graph__memory_search",
            "mcp__memory-graph__memory_get",
            "mcp__memory-graph__memory_neighbors",
            "mcp__memory-graph__memory_status",
            "mcp__memory-graph__memory_capture",
            "mcp__memory-graph__memory_capture_batch",
        ]
        mcp_servers["memory-graph"] = {
            "command": str(PIPX_MEMORY_GRAPH),
            "args": ["serve"],
        }

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
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


def _list_scratch_files(workdir: Path) -> list[dict[str, Any]]:
    """List non-source files the agent created in phase 1."""
    out = []
    src_names = {f"module_{i:02d}.py" for i in range(len(BUG_SPECS))}
    src_names.add("README.md")
    for path in sorted(workdir.iterdir()):
        if path.name in src_names or path.name == ".memory-graph":
            continue
        if path.is_file():
            out.append({"name": path.name, "size_bytes": path.stat().st_size})
        elif path.is_dir():
            out.append({"name": path.name + "/", "size_bytes": -1})
    return out


def _count_notes(workdir: Path) -> int:
    notes_dir = workdir / ".memory-graph" / "notes"
    if not notes_dir.exists():
        return 0
    return sum(1 for _ in notes_dir.rglob("*.md"))


async def run_arm(arm: str) -> dict[str, Any]:
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = WORK_BASE / f"e01-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    _generate_codebase(workdir)

    if arm == "with_memory":
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir),
            check=True,
            capture_output=True,
        )

    print(f"=== e01 ARM: {arm} ===")
    print(f"  workdir: {workdir}")
    print("  phase 1 (investigate) ... ", end="", flush=True)
    p1 = await run_phase(PHASE1_PROMPT, workdir, with_memory=(arm == "with_memory"), max_turns=120)
    scratch = _list_scratch_files(workdir)
    notes_p1 = _count_notes(workdir) if arm == "with_memory" else 0
    tool_counts_p1: dict[str, int] = {}
    for t in p1["tool_calls"]:
        tool_counts_p1[t] = tool_counts_p1.get(t, 0) + 1
    print(f"{p1['seconds']}s  cost=${p1['cost_usd'] or 0:.4f}  "
          f"scratch_files={len(scratch)}  memory_notes={notes_p1}")
    print(f"  phase1 tool calls: {tool_counts_p1}")

    questions = "\n".join(f"Q{i + 1:02d}: {s['question']}" for i, s in enumerate(BUG_SPECS))
    print("  phase 2 (diagnose) ... ", end="", flush=True)
    p2 = await run_phase(
        PHASE2_PROMPT.format(questions=questions),
        workdir,
        with_memory=(arm == "with_memory"),
        max_turns=90,
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
        "scratch_files_after_phase1": scratch,
        "memory_notes_after_phase1": notes_p1,
        "tool_counts_phase1": tool_counts_p1,
        "tool_counts_phase2": tool_counts_p2,
        "total_cost_usd": (p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0),
        "phase1_cost_usd": p1.get("cost_usd") or 0,
        "phase2_cost_usd": p2.get("cost_usd") or 0,
        "total_seconds": round(p1["seconds"] + p2["seconds"], 1),
    }


async def main_async() -> int:
    print("=" * 64)
    print("e01: Realistic baseline replication (30 buggy modules)")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "e01_results.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   {no_mem['score']['hits']}/30  "
          f"total=${no_mem['total_cost_usd']:.4f} ({no_mem['total_seconds']}s)  "
          f"p2=${no_mem['phase2_cost_usd']:.4f}")
    print(f"  with_memory {with_mem['score']['hits']}/30  "
          f"total=${with_mem['total_cost_usd']:.4f} ({with_mem['total_seconds']}s)  "
          f"p2=${with_mem['phase2_cost_usd']:.4f}  "
          f"notes_p1={with_mem['memory_notes_after_phase1']}")
    # Pass criteria
    both_pass = no_mem["score"]["hits"] >= 28 and with_mem["score"]["hits"] >= 28
    cost_ok = with_mem["phase2_cost_usd"] <= 0.5 * no_mem["phase2_cost_usd"]
    verdict = "PASS" if (both_pass and cost_ok) else "FAIL"
    print(f"  verdict: {verdict}  "
          f"(accuracy_pass={both_pass}, cost_pass={cost_ok})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
