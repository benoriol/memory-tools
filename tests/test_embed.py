"""Embedder shape and determinism tests."""

from __future__ import annotations

import os

import numpy as np
import pytest

from memory_recall.embed import EMBEDDING_DIM, DeterministicFakeEmbedder, LocalEmbedder


def test_fake_shape() -> None:
    e = DeterministicFakeEmbedder()
    out = e.embed(["hello", "world", "memory"])
    assert out.shape == (3, EMBEDDING_DIM)
    assert out.dtype == np.float32


def test_fake_deterministic() -> None:
    e = DeterministicFakeEmbedder()
    a = e.embed(["xyz", "abc"])
    b = e.embed(["xyz", "abc"])
    assert np.array_equal(a, b)


def test_fake_distinct() -> None:
    e = DeterministicFakeEmbedder()
    a = e.embed(["alpha"])[0]
    b = e.embed(["beta"])[0]
    assert not np.allclose(a, b)


def test_fake_empty() -> None:
    e = DeterministicFakeEmbedder()
    out = e.embed([])
    assert out.shape == (0, EMBEDDING_DIM)


@pytest.mark.skipif(not os.environ.get("FASTEMBED"), reason="FASTEMBED env not set")
def test_local_embedder_shape() -> None:
    e = LocalEmbedder()
    out = e.embed(["a sentence about memory"])
    assert out.shape == (1, EMBEDDING_DIM)
