# SPDX-License-Identifier: MIT
"""Exercise 38.4, a solution: the Allan deviation of a clock from its time error.

x[i] is the clock's time error at i * tau0 (seconds; a phase record). The fractional frequency
averaged over tau = m * tau0 is (x[i+m] - x[i]) / tau. The overlapping Allan variance at tau is
half the mean square of the difference of two adjacent such averages, over every start i:

    avar(tau) = sum_i (x[i+2m] - 2 x[i+m] + x[i])^2 / (2 tau^2 (N - 2m)).

A second difference of x removes an offset and a constant frequency: the Allan deviation says how
a clock's frequency wanders, not where the clock is or how fast it runs.
"""
import numpy as np


def adev(x, tau0, m):
    """(tau, the overlapping Allan deviation at tau = m * tau0, the number of terms)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("x must be one-dimensional")
    if not (isinstance(m, (int, np.integer)) and m >= 1) or tau0 <= 0:
        raise ValueError(f"m = {m} and tau0 = {tau0}")
    n = x.size - 2 * m
    if n < 1:
        raise ValueError(f"{x.size} samples are too few for m = {m}: need at least {2 * m + 1}")
    tau = m * tau0
    d = x[2 * m:] - 2.0 * x[m:-m] + x[:-2 * m]
    return tau, float(np.sqrt(np.mean(d * d) / (2.0 * tau * tau))), n


def curve(x, tau0):
    """adev() at m = 1, 2, 4, ... while at least 10 terms remain."""
    out = []
    m = 1
    while np.size(x) - 2 * m >= 10:
        out.append(adev(x, tau0, m))
        m *= 2
    return out


def slope(points):
    """The least-squares slope of log(adev) against log(tau): -1 for white phase noise, -1/2 for
    white frequency noise, +1/2 for a random walk of the frequency, +1 for a linear drift of it."""
    t = np.log([p[0] for p in points])
    a = np.log([p[1] for p in points])
    return float(np.polyfit(t, a, 1)[0])
