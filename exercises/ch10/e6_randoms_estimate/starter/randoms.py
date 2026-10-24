# SPDX-License-Identifier: MIT
"""Exercise 10.6: estimating random coincidences from singles rates.

Two detectors record singles at rates s1 and s2 (per second), independently.
A random coincidence is a pair, one single from each, closer in time than the
coincidence window tau: |t2 - t1| <= tau. Times are in seconds.
"""
import bisect
import random


def singles_rate_estimate(s1, s2, tau):
    """Expected random coincidences per second between two independent detectors."""
    # TODO: is the window around t1 really tau wide?
    return tau * s1 * s2


def poisson_times(rate, seconds, rng):
    """Sorted arrival times of a Poisson process: exponential gaps of mean 1/rate."""
    t = rng.expovariate(rate)
    out = []
    while t < seconds:
        out.append(t)
        t += rng.expovariate(rate)
    return out


def count_pairs(t1, t2, tau, offset=0.0):
    """Pairs (a from t1, b from t2) with |(b - offset) - a| <= tau; t2 sorted."""
    # TODO: this only looks after a. Detector 2 can fire first.
    n = 0
    for a in t1:
        lo = bisect.bisect_left(t2, a + offset)
        hi = bisect.bisect_right(t2, a + offset + tau)
        n += hi - lo
    return n


def with_trues(rate1, rate2, true_rate, seconds, jitter, seed):
    """Two detectors' singles: independent backgrounds plus true pairs seen by both."""
    rng = random.Random(seed)
    t1 = poisson_times(rate1, seconds, rng)
    t2 = poisson_times(rate2, seconds, rng)
    trues = poisson_times(true_rate, seconds, rng)
    t1 += [t + rng.gauss(0.0, jitter) for t in trues]
    t2 += [t + rng.gauss(0.0, jitter) for t in trues]
    t1.sort()
    t2.sort()
    return t1, t2, len(trues)
