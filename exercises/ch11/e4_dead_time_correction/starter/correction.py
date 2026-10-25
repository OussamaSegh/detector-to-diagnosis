# SPDX-License-Identifier: MIT
"""Exercise 11.4: correcting a measured rate for dead time.

A detector unit with dead time tau (seconds) that sees a Poisson stream of true
rate n (per second) records m per second:

    non-paralyzable:  m = n / (1 + n tau)
    paralyzable:      m = n exp(-n tau)

Correction runs the other way: from the recorded m back to n.
"""
import math
import random

NON_PARALYZABLE = "non_paralyzable"
PARALYZABLE = "paralyzable"


def recorded_rate(model, n, tau):
    if model == NON_PARALYZABLE:
        return n / (1.0 + n * tau)
    if model == PARALYZABLE:
        return n * math.exp(-n * tau)
    raise ValueError(model)


def true_rate(model, m, tau, branch="low"):
    """The true rate n that records m. A paralyzable unit records at most
    1 / (e tau), at n = 1 / tau, and every lower m has two true rates: branch
    "low" (n < 1 / tau, where a scanner is operated) or "high". NaN when no n
    records m."""
    if model == NON_PARALYZABLE:
        # TODO: invert m = n / (1 + n tau) again, carefully.
        return m / (1.0 + m * tau)
    if model != PARALYZABLE:
        raise ValueError(model)
    # TODO: n exp(-n tau) = m has no closed form (it needs the Lambert W
    # function, which the standard library lacks); solve it numerically, on the
    # requested branch, and return NaN above the maximum. This first-order
    # guess is good only for m tau << 1.
    return m * math.exp(m * tau)


def error_amplification(model, n, tau):
    """How much a relative error in m grows in the corrected n:
    (dn / n) / (dm / m) = (m / n) / (dm / dn)."""
    # TODO: differentiate recorded_rate.
    return 1.0


def simulate_recorded(model, n, tau, seconds, seed=1):
    """Counts a Poisson stream of rate n through one unit: the recorded rate."""
    rng = random.Random(seed)
    t = 0.0
    busy_until = -math.inf
    recorded = 0
    while True:
        t += rng.expovariate(n)
        if t >= seconds:
            return recorded / seconds
        if t >= busy_until:
            recorded += 1
            busy_until = t + tau
        elif model == PARALYZABLE:
            busy_until = t + tau  # a lost event restarts the dead time
