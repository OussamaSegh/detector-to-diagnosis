# SPDX-License-Identifier: MIT
"""Exercise 20.5 solution: numbers for the decisions about a flaky test."""
from __future__ import annotations

import math


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(f, lo=0.0, hi=1.0, steps=100):
    """The p in [lo, hi] where the decreasing function f crosses zero."""
    for _ in range(steps):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# [snippet:interval]
def failure_rate_interval(failures: int, runs: int,
                          confidence: float = 0.95) -> tuple[float, float]:
    """Exact two-sided (Clopper-Pearson) interval of the failure rate."""
    if runs <= 0 or not 0 <= failures <= runs or not 0 < confidence < 1:
        raise ValueError("need 0 <= failures <= runs, runs > 0 and 0 < confidence < 1")
    tail = (1 - confidence) / 2
    # Lower end: the rate at which `failures` or more failures have probability `tail`.
    lower = 0.0 if failures == 0 else _bisect(
        lambda p: tail - (1 - binomial_cdf(failures - 1, runs, p)))
    # Upper end: the rate at which `failures` or fewer have probability `tail`.
    upper = 1.0 if failures == runs else _bisect(lambda p: binomial_cdf(failures, runs, p) - tail)
    return lower, upper
# [/snippet:interval]


def runs_needed(max_rate: float, confidence: float = 0.95) -> int:
    """Reruns without a failure after which the one-sided upper bound is below max_rate."""
    if not 0 < max_rate < 1 or not 0 < confidence < 1:
        raise ValueError("need 0 < max_rate < 1 and 0 < confidence < 1")
    # With no failure in n runs, the bound u solves (1 - u)^n = 1 - confidence.
    return math.ceil(math.log(1 - confidence) / math.log(1 - max_rate))


def worse_after(fail_before: int, runs_before: int, fail_after: int, runs_after: int) -> float:
    """One-sided p-value of Fisher's exact test that the failure rate rose."""
    total_fail = fail_before + fail_after
    total = runs_before + runs_after
    denom = math.comb(total, total_fail)
    # Given the total number of failures, the chance that `fail_after` or more fell after.
    return sum(math.comb(runs_after, k) * math.comb(runs_before, total_fail - k)
               for k in range(fail_after, min(runs_after, total_fail) + 1)) / denom


def retries_hide(rate: float, retries: int) -> float:
    """Probability that a test failing with `rate` per run passes under `retries` retries."""
    if not 0 <= rate <= 1 or retries < 0:
        raise ValueError("need 0 <= rate <= 1 and retries >= 0")
    return 1 - rate ** (retries + 1)
