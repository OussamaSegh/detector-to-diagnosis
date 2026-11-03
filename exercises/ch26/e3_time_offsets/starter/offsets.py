# SPDX-License-Identifier: MIT
"""Exercise 26.3: channel delays from coincident pairs, by least squares.

Each pair (i, j) with time difference dt = t_i - t_j tells you d_i - d_j, up to its noise and the
pair's time-of-flight difference, which is zero on average for a source centered in the ring. The
delays are the least-squares solution of dt = d[ci] - d[cj], with mean zero; the normal equations
are L d = r with L the Laplacian of the graph of pairs (Chapter 26). Only differences are
measured, so the solution is unique only where the graph is connected.

This starter runs and its delays look plausible. TODO: make the tests pass.
"""
import numpy as np


def components(ci, cj, n):
    """The number of connected parts of the graph of pairs, counting only crystals in a pair."""
    return 1


def solve(ci, cj, dt, n, tol=1e-8, max_iter=5000):
    """The delays (mean zero over the crystals in a pair, 0 for the others) that best explain
    dt."""
    # Each crystal's delay as the mean time difference of its pairs, seen from its side.
    deg = (np.bincount(ci, minlength=n) + np.bincount(cj, minlength=n)).astype(float)
    total = np.bincount(ci, dt, n) - np.bincount(cj, dt, n)
    seen = deg > 0
    d = np.where(seen, total / np.maximum(deg, 1.0), 0.0)
    d[seen] -= d[seen].mean()
    return d


def trimmed(ci, cj, dt, n, k=4.0, rounds=8):
    """solve() without the pairs that are not true coincidences. Returns (delays, the pairs
    kept)."""
    keep = np.abs(dt) < 2_000.0  # a true pair is within 2 ns
    return solve(ci[keep], cj[keep], dt[keep], n), keep
