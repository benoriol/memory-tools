"""Embedding providers.

The default `LocalEmbedder` uses FastEmbed's all-MiniLM-L6-v2 model
(~80 MB on disk, 384-dim vectors, fast on CPU). For tests we ship a
deterministic `FakeEmbedder` that avoids the model download.
"""

from memory_graph.embed.base import Embedder, hash_input, normalize
from memory_graph.embed.fake import FakeEmbedder
from memory_graph.embed.local import LocalEmbedder

__all__ = [
    "Embedder",
    "FakeEmbedder",
    "LocalEmbedder",
    "hash_input",
    "normalize",
]
