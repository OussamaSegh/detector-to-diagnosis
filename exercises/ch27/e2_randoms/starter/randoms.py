# SPDX-License-Identifier: MIT
"""Exercise 27.2: the randoms of every line, from the singles and from the delayed coincidences.

Lines are pairs of crystals (i, j) of one ring; `fan[i, j]` is True where the sorter accepts the
pair. Every array is N x N and symmetric.

This starter runs and its estimates have the right shape. TODO: make the tests pass.
"""
import numpy as np

PS = 1e-12


def from_singles(singles, tau_ps, seconds, fan):
    """Expected randoms per line in a run of `seconds`."""
    s = np.asarray(singles, dtype=float)
    # tau s_i s_j: the chance that two singles fall in one window.
    return np.where(fan, tau_ps * PS * np.outer(s, s), 0.0)


def variance_reduced(delayeds, fan, tol=1e-12, max_iter=500):
    """The delayed coincidences with their noise removed: Casey and Hoffman's estimate, each
    line from the fan sums of its two crystals over the total."""
    d = np.asarray(delayeds, dtype=float)
    fan_sum = d.sum(axis=1)
    return np.where(fan, np.outer(fan_sum, fan_sum) / fan_sum.sum(), 0.0)
