# SPDX-License-Identifier: MIT
"""Exercise 38.4: the Allan deviation of a clock from its time error.

x[i] is the clock's time error at i * tau0 (seconds; a phase record). The fractional frequency
averaged over tau = m * tau0 is (x[i+m] - x[i]) / tau.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np


def adev(x, tau0, m):
    """(tau, the spread of the frequency averaged over tau = m * tau0, the number of averages)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.diff(x) / tau0
    k = y.size // m
    means = y[:k * m].reshape(k, m).mean(axis=1)
    return m * tau0, float(np.std(means)), k


def curve(x, tau0):
    """adev() at m = 1, 2, 4, ... while at least 10 terms remain."""
    out = []
    m = 1
    while np.size(x) - 2 * m >= 10:
        out.append(adev(x, tau0, m))
        m *= 2
    return out


def slope(points):
    """The least-squares slope of log(adev) against log(tau)."""
    t = np.log([p[0] for p in points])
    a = np.log([p[1] for p in points])
    return float(np.polyfit(t, a, 1)[0])
