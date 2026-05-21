"""ID generator tests."""

from memory_recall.storage.ids import new_id


def test_length_and_charset() -> None:
    i = new_id()
    assert len(i) == 26
    assert set(i) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def test_monotonic_across_rapid_calls() -> None:
    ids = [new_id(now_ms=1000 + n) for n in range(100)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 100


def test_same_timestamp_distinct() -> None:
    a = new_id(now_ms=42)
    b = new_id(now_ms=42)
    assert a != b
    assert a[:10] == b[:10]
