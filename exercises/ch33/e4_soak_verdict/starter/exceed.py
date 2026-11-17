# SPDX-License-Identifier: MIT
"""Exercise 33.4: what k intervals above the limit out of n say about the fraction of intervals
above it.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import math

Z = {0.90: 1.2816, 0.95: 1.6449, 0.99: 2.3263}  # one-sided normal quantiles


def upper_bound(k, n, confidence=0.95):
    """The largest fraction consistent with k of n above the limit."""
    p = k / n
    return min(1.0, p + Z[confidence] * math.sqrt(p * (1 - p) / n))


def lower_bound(k, n, confidence=0.95):
    """The smallest fraction consistent with k of n above the limit."""
    p = k / n
    return max(0.0, p - Z[confidence] * math.sqrt(p * (1 - p) / n))


def intervals_needed(p_max, confidence=0.95, allowed=0):
    """The fewest intervals for which `allowed` above the limit still shows a fraction <= p_max."""
    n = allowed + 1
    while upper_bound(allowed, n, confidence) > p_max:
        n += 1
    return n


def verdict(k, n, p_max, confidence=0.95):
    """Whether the soak shows a fraction of intervals above the limit within p_max."""
    return "DEMONSTRATED" if k / n <= p_max else "EXCEEDED"
