"""ULID-style id generation."""

from memory_graph.storage.ids import is_valid_id, new_id


def test_id_is_26_chars():
    assert len(new_id()) == 26


def test_id_is_crockford_base32():
    value = new_id()
    assert is_valid_id(value)
    # Crockford excludes I, L, O, U.
    for forbidden in "ILOU":
        assert forbidden not in value


def test_ids_are_unique_in_bulk():
    ids = {new_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_ids_are_time_sortable():
    a = new_id(now_ms=1_000_000)
    b = new_id(now_ms=2_000_000)
    assert a < b


def test_invalid_ids_rejected():
    assert not is_valid_id("")
    assert not is_valid_id("nope")
    assert not is_valid_id("a" * 26)  # lowercase
    assert not is_valid_id("I" * 26)  # forbidden char
