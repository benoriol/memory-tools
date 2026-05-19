"""A deterministic, semantically-useful embedder for tests.

Each whitespace-separated token gets a fixed random unit vector (seeded
by sha256 of the token). An embedding is the L2-normalized sum of its
tokens' vectors. Properties:

  - Identical text → identical embedding (cosine 1.0).
  - Texts sharing vocabulary → high cosine.
  - Texts with disjoint vocabulary → cosine ≈ 0.
  - No model download, no I/O, microseconds per call.

This is enough to exercise the retrieval pipeline meaningfully without
pulling in FastEmbed.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

from memory_graph.embed.base import normalize

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class FakeEmbedder:
    name = "fake"

    def __init__(self, dim: int = 32):
        self.dim = dim
        self._token_cache: dict[str, np.ndarray] = {}

    def _token_vec(self, token: str) -> np.ndarray:
        cached = self._token_cache.get(token)
        if cached is not None:
            return cached
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big")
        rng = np.random.default_rng(seed)
        vec = normalize(rng.standard_normal(self.dim).astype(np.float32))
        self._token_cache[token] = vec
        return vec

    def embed(self, text: str) -> np.ndarray:
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return np.zeros(self.dim, dtype=np.float32)
        accum = np.zeros(self.dim, dtype=np.float32)
        for t in tokens:
            accum = accum + self._token_vec(t)
        return normalize(accum)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed(t) for t in texts]
