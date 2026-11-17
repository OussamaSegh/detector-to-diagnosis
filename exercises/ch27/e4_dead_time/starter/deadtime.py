# SPDX-License-Identifier: MIT
"""Exercise 27.4: a dead-time model and its tau from a decaying source.

A unit with dead time tau records m of the n events per second that reach it. Non-paralyzable:
m = n / (1 + n tau), each recorded event makes the unit dead for tau. Paralyzable: m = n
exp(-n tau), every event, recorded or not, starts the dead time again; its recorded rate has a
maximum, 1 / (e tau) at n = 1 / tau, and each recorded rate below it has two true rates.

A decaying source gives the true rate up to one constant: n(t) = n0 exp(-lambda t). Its recorded
rates over several half-lives tell the kind of dead time and tau.

This starter runs and gives plausible numbers. TODO: make the tests pass.
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


def true_rate(m, tau, kind):
    """The true rate for a recorded rate m."""
    m = np.asarray(m, dtype=float)
    # The two kinds agree at low rates, where m tau is small.
    return m / (1.0 - m * tau)


def fit(t, m, half_life, tau_lo=1e-10, tau_hi=1e-5):
    """For each kind, (tau, n0, spread), and the better kind. Returns {"kind": ..., kind: ...}."""
    t = np.asarray(t, dtype=float)
    m = np.asarray(m, dtype=float)
    lam = math.log(2.0) / half_life
    # At the end the source is weak and dead time negligible: the last point gives n0.
    n0 = float(m[-1] * math.exp(lam * t[-1]))
    n = n0 * np.exp(-lam * t)
    # Non-paralyzable: 1/m - 1/n = tau, averaged over the points.
    tau = float(np.mean(1.0 / m - 1.0 / n))
    out = {kind: (tau, n0, 0.0) for kind in KINDS}
    out["kind"] = "nonparalyzable"
    return out
