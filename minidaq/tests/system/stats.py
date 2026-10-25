# SPDX-License-Identifier: MIT
"""Statistical comparisons for MiniDAQ's system tests (Chapter 19), in plain Python.

A test that compares a run with golden data cannot ask for equal numbers when the data is
random: two runs of a Poisson source never count the same. It asks instead whether the
difference is larger than chance makes likely, and fails when the p-value is below a stated
significance level. Each function returns the p-value: the probability, if both samples come
from the same distribution, of a difference at least as large as the one observed.

Only the standard library is used, so the test tool adds no SOUP; tests/system/test_stats.py
checks these functions against tabulated values and checks that their p-values are uniform
when the null hypothesis holds (Chapter 20: confidence in a test tool).
"""
import math

_EPS = 1e-15
_MAX_ITER = 10_000


def _gamma_series(a, x):
    """Regularized lower incomplete gamma P(a, x) by its series; good for x < a + 1."""
    term = total = 1.0 / a
    n = a
    for _ in range(_MAX_ITER):
        n += 1.0
        term *= x / n
        total += term
        if abs(term) < abs(total) * _EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_fraction(a, x):
    """Regularized upper incomplete gamma Q(a, x) by its continued fraction (modified Lentz);
    good for x >= a + 1."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, _MAX_ITER):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_sf(x, dof):
    """P(X >= x) for X chi-square distributed with dof degrees of freedom."""
    if dof <= 0:
        raise ValueError("chi2_sf: dof must be positive")
    if x <= 0:
        return 1.0
    a, half = dof / 2.0, x / 2.0
    if half < a + 1.0:
        return max(0.0, 1.0 - _gamma_series(a, half))
    return _gamma_fraction(a, half)


def normal_sf(z):
    """P(Z >= z) for a standard normal Z."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def merge_sparse(h1, h2, min_expected=5.0):
    """Merges neighboring bins until each merged bin expects at least min_expected counts in both
    histograms under the null hypothesis (the rule of thumb behind the chi-square approximation).
    Returns the two merged lists."""
    if len(h1) != len(h2):
        raise ValueError("merge_sparse: histograms of different lengths")
    n1, n2 = sum(h1), sum(h2)
    if n1 == 0 or n2 == 0:
        raise ValueError("merge_sparse: an empty histogram")
    f1, f2 = n1 / (n1 + n2), n2 / (n1 + n2)
    m1, m2, a, b = [], [], 0, 0
    for x, y in zip(h1, h2):
        a, b = a + x, b + y
        if (a + b) * min(f1, f2) >= min_expected:
            m1.append(a)
            m2.append(b)
            a = b = 0
    if a or b:  # the remainder joins the last bin
        if m1:
            m1[-1] += a
            m2[-1] += b
        else:
            m1.append(a)
            m2.append(b)
    return m1, m2


# [snippet:homogeneity]
def chi2_homogeneity(h1, h2, min_expected=5.0):
    """Chi-square test that two histograms of counts come from the same distribution, whatever
    their totals. Returns (statistic, degrees of freedom, p-value)."""
    m1, m2 = merge_sparse(h1, h2, min_expected)
    n1, n2 = sum(m1), sum(m2)
    n = n1 + n2
    stat = 0.0
    for x, y in zip(m1, m2):
        col = x + y
        e1, e2 = col * n1 / n, col * n2 / n
        stat += (x - e1) ** 2 / e1 + (y - e2) ** 2 / e2
    dof = len(m1) - 1
    return stat, dof, chi2_sf(stat, dof) if dof > 0 else 1.0
# [/snippet:homogeneity]


def _log_binom_pmf(k, n, p):
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def binomial_two_sided(k, n, p):
    """Exact two-sided binomial test: the probability of an outcome no more likely than k."""
    if not 0.0 < p < 1.0 or not 0 <= k <= n:
        raise ValueError("binomial_two_sided: need 0 < p < 1 and 0 <= k <= n")
    if n > 200_000:  # the normal approximation is far inside its error at these counts
        z = abs(k - n * p) / math.sqrt(n * p * (1.0 - p))
        return min(1.0, 2.0 * normal_sf(z))
    observed = _log_binom_pmf(k, n, p)
    total = 0.0
    for i in range(n + 1):
        lp = _log_binom_pmf(i, n, p)
        if lp <= observed + 1e-7:
            total += math.exp(lp)
    return min(1.0, total)


# [snippet:rates]
def poisson_rates_equal(n1, t1, n2, t2):
    """Two-sided test that two Poisson counts n1 in time t1 and n2 in time t2 have the same rate.
    Given n1 + n2, n1 is binomial with p = t1 / (t1 + t2) when the rates are equal."""
    if n1 + n2 == 0:
        return 1.0
    return binomial_two_sided(n1, n1 + n2, t1 / (t1 + t2))
# [/snippet:rates]


def histogram(values, low, high, bins):
    """Counts of values in `bins` equal bins over [low, high); values outside are not counted."""
    width = (high - low) / bins
    h = [0] * bins
    for v in values:
        if low <= v < high:
            h[min(bins - 1, int((v - low) / width))] += 1
    return h
