"""Synthetic dataset for the polynomial regression demo.

The true signal is `f(x) = sin(2*pi*x) + 0.3 * cos(6*pi*x)` — smooth but
not polynomial. Inputs are sampled from [0, 1]. Gaussian noise is added
at one of three levels.

This module is deliberately tiny and stdlib + numpy only. It exposes:

    get_dataset(noise: float = 0.1, n: int = 200, seed: int = 0)
        -> (X_train, y_train, X_val, y_val)

X_* are 1-D numpy arrays of shape (n,) in [0, 1]; y_* same shape.
"""

from __future__ import annotations

import numpy as np


def _true_signal(x: np.ndarray) -> np.ndarray:
    return np.sin(2 * np.pi * x) + 0.3 * np.cos(6 * np.pi * x)


def get_dataset(
    noise: float = 0.1, n: int = 200, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (X_train, y_train, X_val, y_val). 80/20 split, deterministic."""
    rng = np.random.default_rng(seed)
    X = np.sort(rng.uniform(0.0, 1.0, size=n))
    y = _true_signal(X) + rng.normal(0.0, noise, size=n)
    split = int(0.8 * n)
    return X[:split], y[:split], X[split:], y[split:]


def held_out_test(noise: float = 0.1, n: int = 500, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """A larger held-out test set drawn with a different seed.
    Use only at the very end, after committing to your degree."""
    rng = np.random.default_rng(seed)
    X = np.sort(rng.uniform(0.0, 1.0, size=n))
    y = _true_signal(X) + rng.normal(0.0, noise, size=n)
    return X, y


# Tiny smoke-test if executed directly: dump shapes and a few values.
if __name__ == "__main__":
    for noise in (0.05, 0.2, 0.5):
        Xt, yt, Xv, yv = get_dataset(noise=noise)
        print(f"noise={noise}: train={Xt.shape}, val={Xv.shape}, "
              f"y_train mean={yt.mean():.3f} std={yt.std():.3f}")
