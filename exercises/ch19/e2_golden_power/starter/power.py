# SPDX-License-Identifier: MIT
"""Exercise 19.2 starter: what a comparison with golden data can see.

A statistical comparison that passes says that the difference was not larger than chance makes
likely. It does not say that there was no difference: a small change in a rate that was counted
only a few thousand times passes as often as no change at all. The power of a test is the
probability that it fails when a given difference is real; the smallest difference it finds with
a stated power is what a reviewer needs to know before trusting a pass.

The rate comparison is stats.poisson_rates_equal (minidaq/tests/system/stats.py): two Poisson
counts in equal times, the golden run's and the new run's.
"""
from __future__ import annotations

import math
import random
from statistics import NormalDist

import stats


def min_detectable_ratio(n, alpha=1e-3, power=0.9):
    """The smallest ratio r > 1 of the new run's rate to the golden run's that the comparison of
    two counts in equal times finds with the given power, when the golden run counted n.

    Normal approximation: the new run counts about n*r, the difference n*(r - 1) has a standard
    deviation of about sqrt(n*(1 + r)), and the test fails when the difference exceeds z(1 - alpha/2)
    of them. It does so with probability `power` when n*(r - 1) = (z_a + z_b) * sqrt(n*(1 + r)):
    with k = (z_a + z_b)^2 / n, (r - 1)^2 = k*(1 + r), a quadratic in r."""
    # TODO: refuse nonsense; the power enters through z(power) as well as z(1 - alpha/2).
    z = NormalDist().inv_cdf(1 - alpha / 2)
    return 1 + z * math.sqrt(2 / n)


def poisson(rnd, mean):
    """A Poisson count: by multiplying uniforms below a mean of 30, from the normal distribution
    above it (the error is far below what the tests here can see)."""
    if mean < 30:
        limit, k, p = math.exp(-mean), 0, rnd.random()
        while p > limit:
            k += 1
            p *= rnd.random()
        return k
    return max(0, round(rnd.gauss(mean, math.sqrt(mean))))


def simulated_power(n, ratio, alpha=1e-3, trials=2000, seed=1):
    """The fraction of `trials` simulated pairs of runs, the golden one with mean count n and the new
    one with mean count n*ratio in the same time, that stats.poisson_rates_equal rejects at alpha."""
    # TODO: draw both counts with poisson(), and count the trials the comparison rejects.
    return 0.0


def report(golden, alpha=1e-3, power=0.9):
    """For each count of a golden file, the smallest rate change its comparison finds, in percent."""
    return {key: round(100 * (min_detectable_ratio(golden[key], alpha, power) - 1), 2)
            for key in ("prompts", "delayed")}
