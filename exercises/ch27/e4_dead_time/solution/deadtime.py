# SPDX-License-Identifier: MIT
"""Exercise 27.4, a solution: a dead-time model and its tau from a decaying source.

A unit with dead time tau records m of the n events per second that reach it. Non-paralyzable:
m = n / (1 + n tau), each recorded event makes the unit dead for tau. Paralyzable: m = n
exp(-n tau), every event, recorded or not, starts the dead time again; its recorded rate has a
maximum, 1 / (e tau) at n = 1 / tau, and each recorded rate below it has two true rates.

A decaying source gives the true rate up to one constant: n(t) = n0 exp(-lambda t). Its recorded
rates over several half-lives tell the kind of dead time and tau.
"""
import math

import numpy as np

KINDS = ("nonparalyzable", "paralyzable")


def recorded_rate(n, tau, kind):
    """The rate the unit records for a true rate n."""
    n = np.asarray(n, dtype=float)
    if kind == "nonparalyzable":
        return n / (1.0 + n * tau)
    if kind == "paralyzable":
        return n * np.exp(-n * tau)
    raise ValueError(f"unknown dead-time kind {kind!r}")


def _lambert_w0(x):
    """The principal branch of Lambert's W, w exp(w) = x, for -1/e <= x <= 0, by Newton's method
    from a start near the answer (the series at 0, the expansion at the branch point -1/e)."""
    x = np.asarray(x, dtype=float)
    p = np.sqrt(np.maximum(2.0 * (1.0 + np.e * x), 0.0))
    w = np.where(x > -0.25, x * (1.0 - x), -1.0 + p - p * p / 3.0)
    for _ in range(60):
        ew = np.exp(w)
        slope = ew * (w + 1.0)
        step = np.divide(w * ew - x, slope, out=np.zeros_like(w), where=slope > 1e-12)
        w = np.maximum(w - step, -1.0)
    return w


def true_rate(m, tau, kind):
    """The true rate for a recorded rate m. For a paralyzable unit, the lower of the two: a
    recorded rate above 1 / (e tau) is impossible and raises ValueError, and one near it should
    not be trusted."""
    m = np.asarray(m, dtype=float)
    if kind == "nonparalyzable":
        if np.any(m * tau >= 1.0):
            raise ValueError("a recorded rate at or above 1 / tau")
        return m / (1.0 - m * tau)
    if kind == "paralyzable":
        if np.any(m * tau > 1.0 / math.e):
            raise ValueError(f"a recorded rate above the maximum 1 / (e tau) = {1 / (math.e * tau):.4g}")
        return -_lambert_w0(-m * tau) / tau
    raise ValueError(f"unknown dead-time kind {kind!r}")


def _spread(t, m, half_life, tau, kind):
    """(n0, rms relative spread) of n(t_i) exp(lambda t_i), which a right model makes constant."""
    try:
        n = true_rate(m, tau, kind)
    except ValueError:
        return math.nan, math.inf
    n0s = n * np.exp(math.log(2.0) / half_life * np.asarray(t, dtype=float))
    n0 = float(n0s.mean())
    spread = float(np.sqrt(np.mean((n0s / n0 - 1.0) ** 2)))
    return (n0, spread) if math.isfinite(spread) else (math.nan, math.inf)


def fit(t, m, half_life, tau_lo=1e-10, tau_hi=1e-5):
    """For each kind, the tau that makes the decay-corrected true rates most constant, with n0
    and the remaining spread; and the kind whose spread is smaller. Returns
    {"kind": ..., kind: (tau, n0, spread), ...}."""
    out = {}
    for kind in KINDS:
        hi = tau_hi
        if kind == "paralyzable":  # every recorded rate must be possible
            hi = min(hi, 1.0 / (math.e * float(np.max(m))))
        grid = np.geomspace(tau_lo, hi, 400)
        spread = [_spread(t, m, half_life, tau, kind)[1] for tau in grid]
        k = int(np.argmin(spread))
        a, b = grid[max(k - 1, 0)], grid[min(k + 1, grid.size - 1)]
        for _ in range(80):  # golden section between the grid's neighbors
            c, d = b - (b - a) / 1.618033988749895, a + (b - a) / 1.618033988749895
            if _spread(t, m, half_life, c, kind)[1] < _spread(t, m, half_life, d, kind)[1]:
                b = d
            else:
                a = c
        tau = 0.5 * (a + b)
        n0, s = _spread(t, m, half_life, tau, kind)
        out[kind] = (tau, n0, s)
    out["kind"] = min(KINDS, key=lambda k: out[k][2])
    return out
