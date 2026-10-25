#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the statistics that the system tests rely on (Chapter 19).

A comparison with golden data is only as good as its p-value. These tests check the functions
in stats.py against tabulated quantiles, and check the property that matters most: when both
samples come from the same distribution, a test at the 1% level fails about 1% of the time,
no more (or the system tests would fail at random) and no less (or they would miss real
differences). The second half checks that real differences of the size the system tests must
find are found.
"""
import random
import unittest

import stats


class ChiSquareDistribution(unittest.TestCase):
    def test_the_survival_function_matches_tabulated_quantiles(self):
        # 95% quantiles of the chi-square distribution (NIST/SEMATECH e-Handbook, table 1.3.6.7.4).
        for dof, q95 in ((1, 3.841), (2, 5.991), (5, 11.070), (10, 18.307), (30, 43.773), (100, 124.342)):
            self.assertAlmostEqual(stats.chi2_sf(q95, dof), 0.05, delta=2e-4, msg=f"dof {dof}")
        # Exact cases: two degrees of freedom is an exponential, P = exp(-x / 2).
        for x in (0.1, 1.0, 7.5, 40.0):
            self.assertAlmostEqual(stats.chi2_sf(x, 2), 2.718281828459045 ** (-x / 2), places=12)
        self.assertEqual(stats.chi2_sf(0.0, 4), 1.0)

    def test_the_normal_tail_matches_tabulated_values(self):
        self.assertAlmostEqual(stats.normal_sf(1.959964), 0.025, places=6)
        self.assertAlmostEqual(stats.normal_sf(0.0), 0.5, places=12)


class Binomial(unittest.TestCase):
    def test_the_exact_test_matches_hand_computed_values(self):
        # n = 10, p = 0.5, k = 2: outcomes as unlikely as 2 are 0, 1, 2, 8, 9, 10: 112 / 1024.
        self.assertAlmostEqual(stats.binomial_two_sided(2, 10, 0.5), 112 / 1024, places=12)
        self.assertAlmostEqual(stats.binomial_two_sided(5, 10, 0.5), 1.0, places=12)

    def test_equal_rates_in_different_times(self):
        self.assertGreater(stats.poisson_rates_equal(1000, 1.0, 2000, 2.0), 0.9)
        self.assertLess(stats.poisson_rates_equal(1200, 1.0, 2000, 2.0), 1e-5)  # z = 5.0


def multinomial(rng, probabilities, n):
    cumulative, total = [], 0.0
    for p in probabilities:
        total += p
        cumulative.append(total)
    h = [0] * len(probabilities)
    for _ in range(n):
        u = rng.random() * total
        lo, hi = 0, len(cumulative) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cumulative[mid] < u:
                lo = mid + 1
            else:
                hi = mid
        h[lo] += 1
    return h


def poisson_count(rng, rate, seconds):
    """The number of events of a Poisson process with this rate in this time."""
    n, t = 0, rng.expovariate(rate)
    while t < seconds:
        n += 1
        t += rng.expovariate(rate)
    return n


SPECTRUM = [1, 2, 4, 8, 14, 20, 24, 20, 14, 8, 4, 2, 1, 0.5, 0.2, 0.1]


class Calibration(unittest.TestCase):
    def test_p_values_are_uniform_when_the_samples_agree(self):
        rng = random.Random(19)
        trials, level = 2000, 0.01
        p = [stats.chi2_homogeneity(multinomial(rng, SPECTRUM, 2000), multinomial(rng, SPECTRUM, 6000))[2]
             for _ in range(trials)]
        # Under the null hypothesis the number of p-values below a level is binomial(trials, level).
        for lvl in (level, 0.05, 0.5):
            below = sum(x < lvl for x in p)
            self.assertGreater(stats.binomial_two_sided(below, trials, lvl), 0.001,
                               f"{below} of {trials} p-values below {lvl}")

    def test_rate_test_p_values_are_uniform_when_the_rates_agree(self):
        rng = random.Random(20)
        trials = 2000
        below = 0
        for _ in range(trials):
            n1, n2 = poisson_count(rng, 500.0, 1.0), poisson_count(rng, 500.0, 2.0)
            below += stats.poisson_rates_equal(n1, 1.0, n2, 2.0) < 0.05
        # The exact test is conservative for discrete counts: at most the level, not much less.
        self.assertLess(below, trials * 0.05 + 3 * (trials * 0.05) ** 0.5)
        self.assertGreater(below, trials * 0.02)


class Power(unittest.TestCase):
    def test_a_shifted_peak_is_found(self):
        rng = random.Random(21)
        shifted = SPECTRUM[1:] + [0.0]  # the peak one bin lower, as a 3% gain error would put it
        p = stats.chi2_homogeneity(multinomial(rng, SPECTRUM, 20_000), multinomial(rng, shifted, 20_000))[2]
        self.assertLess(p, 1e-6)

    def test_a_two_percent_rate_difference_is_found_at_a_million_counts(self):
        self.assertLess(stats.poisson_rates_equal(1_000_000, 1.0, 1_020_000, 1.0), 1e-6)


class Histograms(unittest.TestCase):
    def test_sparse_bins_are_merged_and_counts_kept(self):
        m1, m2 = stats.merge_sparse([0, 1, 30, 40, 1, 0], [0, 2, 60, 80, 1, 1], 5)
        self.assertEqual((sum(m1), sum(m2)), (72, 144))
        self.assertTrue(all(a + b >= 15 for a, b in zip(m1, m2)), (m1, m2))

    def test_histogram_bins(self):
        self.assertEqual(stats.histogram([0.0, 0.5, 0.99, 1.0, 2.5, -1, 3.0], 0.0, 3.0, 3), [3, 1, 1])


if __name__ == "__main__":
    unittest.main(verbosity=1)
