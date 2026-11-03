# SPDX-License-Identifier: MIT
"""Exercise 27.2: the randoms of every line, from the singles and from the delayed coincidences.

Lines are pairs of crystals (i, j) of one ring; `fan[i, j]` is True where the sorter accepts the
pair. Every array is N x N and symmetric.
"""
import numpy as np

PS = 1e-12


# [snippet:singles]
def from_singles(singles, tau_ps, seconds, fan):
    """Expected randoms per line in a run of `seconds`: 2 tau s_i s_j per second for the singles
    rates s = singles / seconds. A single opens a window of tau and falls in the windows of the
    singles up to tau before it: the pair is within tau either way round, hence 2 tau."""
    rate = np.asarray(singles, dtype=float) / seconds
    return np.where(fan, 2.0 * tau_ps * PS * np.outer(rate, rate) * seconds, 0.0)
# [/snippet:singles]


# [snippet:reduced]
def variance_reduced(delayeds, fan, tol=1e-12, max_iter=500):
    """The delayed coincidences with their noise removed. Randoms factorize, R_ij = x_i x_j on the
    fan, so find x from the fan sums of the delayeds, D_i = x_i * sum over j in i's fan of x_j,
    and return x_i x_j: each line's estimate then rests on two fan sums of hundreds of counts
    instead of its own few. The fixed point x_i = D_i / sum_j x_j converges when damped by the
    geometric mean of two steps."""
    d = np.asarray(delayeds, dtype=float)
    f = np.asarray(fan, dtype=float)
    fan_sum = d.sum(axis=1)
    x = np.sqrt(np.maximum(fan_sum, 0) / np.maximum(f.sum(axis=1), 1))
    for _ in range(max_iter):
        seen = f @ x
        new = np.where(seen > 0, fan_sum / np.where(seen > 0, seen, 1.0), 0.0)
        new = np.sqrt(new * x)
        done = np.abs(new - x).max() <= tol * max(x.max(), 1e-300)
        x = new
        if done:
            break
    return np.where(fan, np.outer(x, x), 0.0)
# [/snippet:reduced]
