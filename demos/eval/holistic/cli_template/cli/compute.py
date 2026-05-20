"""Statistical computations for the CLI."""

from __future__ import annotations


def sum_values(values: list[float]) -> float:
    """Return the sum. Integer inputs should produce integer output."""
    # BUG #1: This always returns float; sum of integers should stay int.
    return sum(values) + 0.0


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def stats(values: list[float]) -> dict[str, float]:
    """Compute sum, mean, min, max."""
    if not values:
        return {"sum": 0, "mean": 0.0, "min": 0, "max": 0}
    return {
        "sum": sum_values(values),
        "mean": mean(values),
        "min": min(values),
        "max": max(values),
    }
