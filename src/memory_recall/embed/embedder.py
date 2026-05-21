"""Embedder protocol + local FastEmbed + deterministic fake."""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

EMBEDDING_DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    """Maps a list of texts to a (N, D) float32 matrix."""

    dim: int
    model_name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class LocalEmbedder:
    """FastEmbed MiniLM-L6-v2 (384-dim). Loads lazily on first call."""

    dim = EMBEDDING_DIM
    model_name = MODEL_NAME

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        self._load()
        vectors = list(self._model.embed(texts))
        out = np.asarray(vectors, dtype=np.float32)
        return out


class DeterministicFakeEmbedder:
    """Hashes each text to a stable 384-dim float32 vector. For tests."""

    dim = EMBEDDING_DIM
    model_name = "deterministic-fake-v0"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        rows = []
        for t in texts:
            rows.append(_hash_vector(t, self.dim))
        return np.vstack(rows).astype(np.float32)


def _hash_vector(text: str, dim: int) -> np.ndarray:
    # Expand a SHA-256 digest by re-hashing with counters until we have dim floats.
    needed_bytes = dim * 4
    buf = bytearray()
    counter = 0
    seed = text.encode("utf-8")
    while len(buf) < needed_bytes:
        h = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        buf.extend(h)
        counter += 1
    arr = np.frombuffer(bytes(buf[:needed_bytes]), dtype=np.uint32).astype(np.float32)
    # Map to [-1, 1] then unit-normalize so cosine similarity is well-behaved.
    arr = (arr / np.float32(2**31)) - np.float32(1.0)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr
