"""Local embedder backed by FastEmbed (all-MiniLM-L6-v2 by default).

The model is downloaded lazily on first use (~80 MB). Subsequent calls
reuse the loaded model in-process, so latency drops to a few ms per
embed after warmup.
"""

from __future__ import annotations

import numpy as np

from memory_graph.embed.base import normalize

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIM = 384


class LocalEmbedder:
    """Wraps FastEmbed's TextEmbedding."""

    def __init__(self, model_name: str = DEFAULT_MODEL, dim: int = DEFAULT_DIM):
        self.name = model_name
        self.dim = dim
        self._model = None

    @property
    def model(self):
        if self._model is None:
            # Imported lazily so tests that use FakeEmbedder don't pay the
            # cost of pulling in fastembed (and indirectly onnxruntime).
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.name)
        return self._model

    def embed(self, text: str) -> np.ndarray:
        vecs = list(self.model.embed([text]))
        return normalize(vecs[0])

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        vecs = list(self.model.embed(texts))
        return [normalize(v) for v in vecs]
