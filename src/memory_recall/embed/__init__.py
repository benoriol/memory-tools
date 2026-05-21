"""Embedders: local FastEmbed and deterministic fake."""

from memory_recall.embed.embedder import (
    EMBEDDING_DIM,
    MODEL_NAME,
    DeterministicFakeEmbedder,
    Embedder,
    LocalEmbedder,
)

__all__ = [
    "EMBEDDING_DIM",
    "MODEL_NAME",
    "DeterministicFakeEmbedder",
    "Embedder",
    "LocalEmbedder",
]
