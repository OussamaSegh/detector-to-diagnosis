# SPDX-License-Identifier: MIT
"""Exercise 26.3: channel delays from coincident pairs, by least squares.

Each pair (i, j) with time difference dt = t_i - t_j tells you d_i - d_j, up to its noise and the
pair's time-of-flight difference, which is zero on average for a source centered in the ring. The
delays are the least-squares solution of dt = d[ci] - d[cj], with mean zero; the normal equations
are L d = r with L the Laplacian of the graph of pairs (Chapter 26). Only differences are
measured, so the solution is unique only where the graph is connected.
"""
import numpy as np


# [snippet:components]
def components(ci, cj, n):
    """The number of connected parts of the graph of pairs, counting only crystals in a pair.
    Every crystal takes the smallest label among its partners' until nothing changes."""
    label = np.arange(n)
    seen = np.zeros(n, dtype=bool)
    seen[ci] = True
    seen[cj] = True
    while True:
        low = label.copy()
        np.minimum.at(low, ci, label[cj])
        np.minimum.at(low, cj, label[ci])
        low = low[low]  # follow labels of labels: halves the rounds on a long chain
        if np.array_equal(low, label):
            break
        label = low
    return len(np.unique(label[seen]))
# [/snippet:components]


# [snippet:cg]
def solve(ci, cj, dt, n, tol=1e-8, max_iter=5000):
    """The delays (mean zero over the crystals in a pair, 0 for the others) that best explain dt,
    by conjugate gradients on L d = r. Refuses a graph in more than one part, whose parts would
    each have their own unknown constant."""
    if components(ci, cj, n) != 1:
        raise ValueError("the pairs do not connect every crystal with every other")
    deg = (np.bincount(ci, minlength=n) + np.bincount(cj, minlength=n)).astype(float)
    seen = deg > 0

    def lap(x):
        return deg * x - np.bincount(ci, x[cj], n) - np.bincount(cj, x[ci], n)

    r = np.bincount(ci, dt, n) - np.bincount(cj, dt, n)
    d = np.zeros(n)
    res = r.copy()
    p = res.copy()
    rr = res @ res
    stop = tol * np.sqrt(rr)
    for _ in range(max_iter):
        if np.sqrt(rr) <= stop:
            break
        lp = lap(p)
        alpha = rr / (p @ lp)
        d += alpha * p
        res -= alpha * lp
        rr, rr_old = res @ res, rr
        p = res + (rr / rr_old) * p
    d[seen] -= d[seen].mean()
    return d
# [/snippet:cg]


# [snippet:trim]
def trimmed(ci, cj, dt, n, k=4.0, rounds=8):
    """solve() without the pairs whose residual is beyond k robust standard deviations (1.4826
    times the median absolute residual), repeated until the set of pairs no longer changes.
    Returns (delays, the pairs kept)."""
    keep = np.ones(dt.size, dtype=bool)
    for _ in range(rounds):
        d = solve(ci[keep], cj[keep], dt[keep], n)
        resid = dt - (d[ci] - d[cj])
        sigma = 1.4826 * np.median(np.abs(resid[keep]))
        new = np.abs(resid) <= k * sigma
        if np.array_equal(new, keep):
            break
        keep = new
    return d, keep
# [/snippet:trim]
