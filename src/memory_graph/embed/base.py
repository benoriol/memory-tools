"""Embedder protocol and helpers."""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """An object that turns text into a fixed-size float32 vector."""

    dim: int
    name: str

    def embed(self, text: str) -> np.ndarray: ...

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]: ...


def hash_input(text: str) -> str:
    """SHA-256 of the embedder input. Used to skip re-embedding unchanged content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize so cosine similarity reduces to a dot product."""
    vec = vec.astype(np.float32, copy=False)
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return vec
    return vec / norm


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors. Assumes finite values."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_embed_input(title: str, summary: str, body: str, body_chars: int = 1500) -> str:
    """Compose the canonical text we feed to the embedder.

    Title + summary dominate; only a prefix of the body is included so very
    long notes don't dilute the signal.
    """
    parts = [title.strip()]
    if summary.strip():
        parts.append(summary.strip())
    snippet = body.strip()[:body_chars]
    if snippet:
        parts.append(snippet)
    return "\n\n".join(parts)
