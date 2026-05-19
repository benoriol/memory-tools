"""ULID-style ids: lexicographically sortable, 26 Crockford-base32 chars.

Format (per the ULID spec):
  - 48 bits of millisecond timestamp
  - 80 bits of randomness
  - Encoded with Crockford's base32 alphabet (no I, L, O, U).

Sortable by creation time; collision-resistant; opaque to humans.
"""

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode(value: int, length: int) -> str:
    """Encode an unsigned integer as Crockford base32 of exactly `length` chars."""
    if value < 0:
        raise ValueError("value must be non-negative")
    chars = []
    for _ in range(length):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    if value:
        raise ValueError("value too large for given length")
    return "".join(reversed(chars))


def new_id(now_ms: int | None = None) -> str:
    """Generate a new ULID. `now_ms` is for tests; defaults to current time."""
    ts = int(time.time() * 1000) if now_ms is None else now_ms
    rand = int.from_bytes(os.urandom(10), "big")
    return _encode(ts, 10) + _encode(rand, 16)


def is_valid_id(value: str) -> bool:
    """Return True if `value` looks like a ULID we'd generate."""
    if len(value) != 26:
        return False
    return all(c in _CROCKFORD for c in value)
