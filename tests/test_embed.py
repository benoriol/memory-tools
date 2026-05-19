"""Embedder protocol, deterministic fake, and helpers.

The local FastEmbed model is exercised in a separate slow test that is
opt-in (FASTEMBED=1) so the default test run stays under 1s.
"""

import os

import numpy as np
import pytest

from memory_graph.embed import FakeEmbedder, hash_input, normalize
from memory_graph.embed.base import build_embed_input, cosine


def test_hash_input_is_stable():
    assert hash_input("hello") == hash_input("hello")
    assert hash_input("hello") != hash_input("world")
    assert len(hash_input("x")) == 64  # sha256 hex digest


def test_normalize_unit_length():
    v = np.array([3.0, 4.0], dtype=np.float32)
    n = normalize(v)
    assert pytest.approx(float(np.linalg.norm(n))) == 1.0


def test_normalize_zero_vector_safe():
    v = np.zeros(4, dtype=np.float32)
    assert np.array_equal(normalize(v), v)


def test_cosine_orthogonal_and_identical():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert pytest.approx(cosine(a, b)) == 0.0
    assert pytest.approx(cosine(a, a)) == 1.0


def test_fake_embedder_is_deterministic():
    e = FakeEmbedder(dim=16)
    a = e.embed("hello world")
    b = e.embed("hello world")
    assert np.array_equal(a, b)
    assert a.shape == (16,)
    assert a.dtype == np.float32


def test_fake_embedder_different_texts_differ():
    e = FakeEmbedder(dim=64)
    a = e.embed("Postgres migration locking")
    b = e.embed("Frontend pagination cursor")
    # Unrelated random vectors in 64-d should have small cosine.
    assert abs(cosine(a, b)) < 0.5
    # Identical input is exactly 1.0.
    assert pytest.approx(cosine(a, e.embed("Postgres migration locking"))) == 1.0


def test_fake_embedder_batch_matches_single():
    e = FakeEmbedder()
    texts = ["alpha", "beta", "gamma"]
    batch = e.embed_batch(texts)
    for t, v in zip(texts, batch):
        assert np.array_equal(v, e.embed(t))


def test_build_embed_input_prefers_summary():
    text = build_embed_input(
        title="T",
        summary="S",
        body="B" * 5000,
    )
    assert text.startswith("T\n\nS\n\n")
    # Body is truncated to 1500 chars.
    assert "B" * 1501 not in text


def test_build_embed_input_handles_empty_summary():
    text = build_embed_input(title="T", summary="", body="Body here")
    assert "S" not in text
    assert text == "T\n\nBody here"


@pytest.mark.skipif(
    os.environ.get("FASTEMBED") != "1",
    reason="set FASTEMBED=1 to exercise the real model (downloads ~80MB on first run)",
)
def test_local_embedder_real_model_smoke():
    """Sanity check that the real LocalEmbedder loads and produces a unit vector."""
    from memory_graph.embed import LocalEmbedder

    e = LocalEmbedder()
    v = e.embed("a quick test of the local embedder")
    assert v.shape == (e.dim,)
    assert pytest.approx(float(np.linalg.norm(v)), rel=1e-3) == 1.0
