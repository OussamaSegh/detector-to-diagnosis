# SPDX-License-Identifier: MIT
"""Exercise 33.4, a solution: what k intervals above the limit out of n say about the fraction of
intervals above it, with exact binomial bounds (Clopper and Pearson), standard library only."""
import math


def _cdf(k, n, p):
    """P(X <= k) for X binomial (n, p), summed in log space so that n of 10^6 does not overflow."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp
             + (n - i) * lq for i in range(k + 1)]
    top = max(terms)
    return min(1.0, math.exp(top) * math.fsum(math.exp(t - top) for t in terms))


def _check(k, n, confidence):
    if not (isinstance(n, int) and isinstance(k, int) and 0 <= k <= n and n >= 1):
        raise ValueError(f"{k} intervals above out of {n}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence {confidence}")


def _solve(f, target):
    """The p in [0, 1] where the decreasing function f crosses target, by bisection."""
    lo, hi = 0.0, 1.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def upper_bound(k, n, confidence=0.95):
    """The largest fraction p still consistent with k or fewer of n: P(X <= k; n, p) = 1 - c."""
    _check(k, n, confidence)
    if k == n:
        return 1.0
    return _solve(lambda p: _cdf(k, n, p), 1.0 - confidence)


def lower_bound(k, n, confidence=0.95):
    """The smallest fraction p still consistent with k or more of n: P(X >= k; n, p) = 1 - c."""
    _check(k, n, confidence)
    if k == 0:
        return 0.0
    return _solve(lambda p: _cdf(k - 1, n, p), confidence)


def intervals_needed(p_max, confidence=0.95, allowed=0):
    """The fewest intervals for which `allowed` above the limit still shows a fraction <= p_max."""
    if not 0.0 < p_max < 1.0:
        raise ValueError(f"fraction {p_max}")
    n = allowed + 1
    while upper_bound(allowed, n, confidence) > p_max:
        n += 1
    return n


def verdict(k, n, p_max, confidence=0.95):
    """DEMONSTRATED when even the upper bound is within p_max, EXCEEDED when even the lower bound is
    above it, INCONCLUSIVE when the soak was too short to tell."""
    if upper_bound(k, n, confidence) <= p_max:
        return "DEMONSTRATED"
    if lower_bound(k, n, confidence) > p_max:
        return "EXCEEDED"
    return "INCONCLUSIVE"
