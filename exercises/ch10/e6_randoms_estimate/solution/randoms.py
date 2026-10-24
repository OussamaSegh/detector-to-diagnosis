# SPDX-License-Identifier: MIT
"""Exercise 10.6: estimating random coincidences from singles rates.

Two detectors record singles at rates s1 and s2 (per second), independently.
A random coincidence is a pair, one single from each, closer in time than the
coincidence window tau: |t2 - t1| <= tau. Times are in seconds.
"""
import bisect
import random


# [snippet:formula]
def singles_rate_estimate(s1, s2, tau):
    """Expected random coincidences per second between two independent detectors.

    For each single in detector 1, detector 2 fires within [t1 - tau, t1 + tau],
    an interval of 2 tau, with probability about 2 tau s2 (when 2 tau s2 << 1).
    """
    return 2.0 * tau * s1 * s2
# [/snippet:formula]


def poisson_times(rate, seconds, rng):
    """Sorted arrival times of a Poisson process: exponential gaps of mean 1/rate."""
    t = rng.expovariate(rate)
    out = []
    while t < seconds:
        out.append(t)
        t += rng.expovariate(rate)
    return out


# [snippet:count]
def count_pairs(t1, t2, tau, offset=0.0):
    """Pairs (a from t1, b from t2) with |(b - offset) - a| <= tau; t2 sorted.

    offset = 0 counts prompt coincidences; offset = delay counts the delayed
    window, where no pair can come from the same decay.
    """
    n = 0
    for a in t1:
        lo = bisect.bisect_left(t2, a + offset - tau)
        hi = bisect.bisect_right(t2, a + offset + tau)
        n += hi - lo
    return n
# [/snippet:count]


def with_trues(rate1, rate2, true_rate, seconds, jitter, seed):
    """Two detectors' singles: independent backgrounds plus true pairs seen by both.

    Each true pair is one decay detected in both detectors, with Gaussian time
    jitter `jitter` (seconds) on each side. Returns (t1, t2, number of trues).
    """
    rng = random.Random(seed)
    t1 = poisson_times(rate1, seconds, rng)
    t2 = poisson_times(rate2, seconds, rng)
    trues = poisson_times(true_rate, seconds, rng)
    t1 += [t + rng.gauss(0.0, jitter) for t in trues]
    t2 += [t + rng.gauss(0.0, jitter) for t in trues]
    t1.sort()
    t2.sort()
    return t1, t2, len(trues)
