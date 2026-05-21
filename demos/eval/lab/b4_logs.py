"""B4: Heterogeneous-format log anomaly detection.

50 log files, each from a different fictional service. Each file uses its own
format (JSON-lines, key=val, CSV, syslog-ish prose). Each file has ~500 events.
A subset of services have ONE of three anomaly patterns:
  - A: long gap with no heartbeat (>30 min)
  - B: a burst of 5+ identical error codes within 10s
  - C: a non-monotonic timestamp (out-of-order events)

The agent must report every (service, pattern) pair.

Why this might need memory: many small per-service findings to track.

Loophole still open: agent writes a per-format parser, runs detection per
file, dumps results.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

NAME = "b4_logs"
DESCRIPTION = "Detect anomalies across 50 heterogeneous log files"
LOOPHOLE_CLOSED = "no fixed format; per-file parsing required"

N_SERVICES = 50
EVENTS_PER_SERVICE = 500
FORMATS = ["jsonl", "kv", "csv", "syslog"]
SERVICE_NAMES = [
    "api", "auth", "billing", "cache", "dispatch", "edge", "feed", "gauge",
    "hooks", "indexer", "jobs", "keyring", "ledger", "mesh", "notify",
    "orders", "pipes", "queue", "router", "search", "store", "tally", "users",
    "vault", "webhooks", "xform", "yields", "zoning",
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor",
]
PATTERNS = ["A", "B", "C", "none"]


def _fmt(fmt: str, t: datetime, code: str, msg: str) -> str:
    iso = t.isoformat()
    if fmt == "jsonl":
        return json.dumps({"ts": iso, "code": code, "msg": msg})
    if fmt == "kv":
        return f"ts={iso} code={code} msg={msg!r}"
    if fmt == "csv":
        return f"{iso},{code},{msg}"
    # syslog-ish prose
    return f"{t.strftime('%b %d %H:%M:%S')} [{code}] {msg}"


def _generate_service(name: str, fmt: str, pattern: str, rng: random.Random) -> str:
    start = datetime(2026, 1, 1, 8, 0, 0)
    events = []
    cur = start
    codes_ok = ["OK", "INFO", "DEBUG"]
    codes_err = ["E101", "E202", "E303", "E404", "E505"]

    # Decide where to inject anomaly
    inject_at = rng.randint(50, EVENTS_PER_SERVICE - 50)
    inject_code = rng.choice(codes_err)

    for i in range(EVENTS_PER_SERVICE):
        if pattern == "A" and i == inject_at:
            cur = cur + timedelta(minutes=rng.randint(35, 90))  # gap > 30 min
        elif pattern == "B" and inject_at <= i < inject_at + 5:
            # burst of identical errors within 10s
            cur = events_last_time = cur + timedelta(seconds=rng.randint(0, 1))
            events.append(_fmt(fmt, cur, inject_code, "burst error"))
            continue
        elif pattern == "C" and i == inject_at:
            cur = cur - timedelta(minutes=rng.randint(5, 20))  # backwards
        else:
            cur = cur + timedelta(seconds=rng.randint(2, 60))
        code = rng.choice(codes_ok if rng.random() < 0.85 else codes_err)
        events.append(_fmt(fmt, cur, code, f"event_{i}"))
    return "\n".join(events) + "\n"


def prepare(workdir: Path, *, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed + 12345)
    services = rng.sample(SERVICE_NAMES, k=N_SERVICES)

    truth: list[dict] = []
    for svc in services:
        fmt = rng.choice(FORMATS)
        # ~ 1/3 of services have anomalies
        pat = rng.choice(["A", "B", "C", "none", "none"])
        text = _generate_service(svc, fmt, pat, rng)
        ext = {"jsonl": ".jsonl", "kv": ".log", "csv": ".csv", "syslog": ".syslog"}[fmt]
        (workdir / f"{svc}{ext}").write_text(text)
        if pat != "none":
            truth.append({"service": svc, "pattern": pat})

    (workdir / "_ground_truth.json").write_text(json.dumps({"truth": truth}, indent=2))
    return {"n_services": N_SERVICES, "answer": truth}


PROMPT = """\
This directory contains {n_services} log files, one per fictional service.
Each file has ~500 events. The files use four different formats:

  - .jsonl    each line is a JSON object with ts/code/msg
  - .log      each line is ts=... code=... msg=...
  - .csv      ISO_TIMESTAMP,CODE,MSG
  - .syslog   "MMM DD HH:MM:SS [CODE] msg"

Some services exhibit one of three anomaly patterns:

  A: a gap of MORE than 30 minutes between two consecutive events
  B: a burst of 5+ events all sharing the same error code within 10 seconds
  C: a non-monotonic timestamp — an event whose ts is EARLIER than the
     previous event in the same file

Your task: find every (service, pattern) pair. A service may have at most
one anomaly. Services with no anomaly should be omitted.

Output ONLY the last line:

ANOMALIES: <service1>:<A|B|C>, <service2>:<A|B|C>, ...

Sorted alphabetically by service. If no anomalies, output:
ANOMALIES: (none)
"""


def grade(text: str, gt: dict) -> dict[str, Any]:
    m = re.search(r"ANOMALIES\s*:\s*(.+?)(?:\n|$)", text or "", re.IGNORECASE)
    if not m:
        return {"parsed": False, "score": 0.0, "reason": "no ANOMALIES line"}
    payload = m.group(1).strip()
    if payload.lower() in {"(none)", "none", "-"}:
        reported_pairs = set()
    else:
        reported_pairs = set()
        for tok in re.split(r"[,\s]+", payload):
            if ":" in tok:
                svc, pat = tok.split(":", 1)
                reported_pairs.add((svc.strip(), pat.strip().upper()))
    truth_pairs = {(t["service"], t["pattern"]) for t in gt["answer"]}
    tp = len(reported_pairs & truth_pairs)
    fp = len(reported_pairs - truth_pairs)
    fn = len(truth_pairs - reported_pairs)
    p = tp / (tp + fp) if (tp + fp) else (1.0 if not truth_pairs else 0.0)
    r = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {
        "parsed": True,
        "score": round(f1, 3),
        "precision": round(p, 3),
        "recall": round(r, 3),
        "tp": tp, "fp": fp, "fn": fn,
        "n_truth": len(truth_pairs),
        "n_reported": len(reported_pairs),
    }
