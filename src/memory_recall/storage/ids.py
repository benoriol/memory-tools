"""ULID-style sortable 26-char identifiers."""

from __future__ import annotations

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIME_LEN = 10
_RAND_LEN = 16


def _encode(value: int, length: int) -> str:
    out = [""] * length
    for i in range(length - 1, -1, -1):
        out[i] = _CROCKFORD[value & 0x1F]
        value >>= 5
    return "".join(out)


def new_id(now_ms: int | None = None) -> str:
    """Return a 26-char Crockford-base32 ULID-like id (sortable by time)."""
    ts = now_ms if now_ms is not None else int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    return _encode(ts, _TIME_LEN) + _encode(rand, _RAND_LEN)
