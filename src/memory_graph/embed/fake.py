"""A deterministic embedder for tests.

Hashes the input text into a seeded RNG and draws a fixed-size random
vector. Same text → same vector. Different texts → different vectors,
so cosine similarity between unrelated inputs is near 0 and identical
inputs is exactly 1.
"""

from __future__ import annotations

import hashlib

import numpy as np

from memory_graph.embed.base import normalize


class FakeEmbedder:
    name = "fake"

    def __init__(self, dim: int = 32):
        self.dim = dim

    def _seed(self, text: str) -> int:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    def embed(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(self._seed(text))
        vec = rng.standard_normal(self.dim).astype(np.float32)
        return normalize(vec)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed(t) for t in texts]
