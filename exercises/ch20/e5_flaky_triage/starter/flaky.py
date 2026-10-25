# SPDX-License-Identifier: MIT
"""Exercise 20.5 starter: numbers for the decisions about a flaky test."""
from __future__ import annotations

import math


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def failure_rate_interval(failures: int, runs: int,
                          confidence: float = 0.95) -> tuple[float, float]:
    """Exact two-sided (Clopper-Pearson) interval of the failure rate."""
    raise NotImplementedError  # TODO: bisection on binomial_cdf for each end


def runs_needed(max_rate: float, confidence: float = 0.95) -> int:
    """Reruns without a failure after which the one-sided upper bound is below max_rate."""
    raise NotImplementedError  # TODO


def worse_after(fail_before: int, runs_before: int, fail_after: int, runs_after: int) -> float:
    """One-sided p-value of Fisher's exact test that the failure rate rose."""
    raise NotImplementedError  # TODO: hypergeometric tail


def retries_hide(rate: float, retries: int) -> float:
    """Probability that a test failing with `rate` per run passes under `retries` retries."""
    raise NotImplementedError  # TODO
