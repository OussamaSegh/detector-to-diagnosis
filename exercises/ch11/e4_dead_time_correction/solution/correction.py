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


# [snippet:invert]
def true_rate(model, m, tau, branch="low"):
    """The true rate n that records m. A paralyzable unit records at most
    1 / (e tau), at n = 1 / tau, and every lower m has two true rates: branch
    "low" (n < 1 / tau, where a scanner is operated) or "high". NaN when no n
    records m."""
    if model == NON_PARALYZABLE:
        return m / (1.0 - m * tau) if m * tau < 1.0 else math.nan
    if model != PARALYZABLE:
        raise ValueError(model)
    if m * tau > (1.0 + 1e-12) / math.e:  # allow for rounding at the maximum
        return math.nan
    # n exp(-n tau) rises on [0, 1 / tau] and falls beyond: bisect on the
    # chosen side. 200 halvings are more than double precision needs.
    peak = 1.0 / tau
    if branch == "low":
        lo, hi = 0.0, peak
    elif branch == "high":
        lo, hi = peak, 2.0 * peak
        while recorded_rate(PARALYZABLE, hi, tau) > m:
            hi *= 2.0
    else:
        raise ValueError(branch)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        below = recorded_rate(PARALYZABLE, mid, tau) < m
        if below == (branch == "low"):
            lo = mid  # on the low branch, below m means the root is higher
        else:
            hi = mid
    return 0.5 * (lo + hi)
# [/snippet:invert]


def error_amplification(model, n, tau):
    """How much a relative error in m grows in the corrected n:
    (dn / n) / (dm / m) = (m / n) / (dm / dn)."""
    x = n * tau
    if model == NON_PARALYZABLE:
        return 1.0 + x
    if model == PARALYZABLE:
        return 1.0 / (1.0 - x) if x != 1.0 else math.inf
    raise ValueError(model)


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
