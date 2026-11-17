# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 33.4: exact bounds on the fraction of soak intervals above a
limit, and a verdict that says when a soak was too short to tell."""
import math
import unittest

import exceed as e


def pmf(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


class Bounds(unittest.TestCase):
    def test_none_above_has_the_closed_form(self):
        # P(X = 0) = (1 - p)^n = 1 - c gives p = 1 - (1 - c)^(1/n).
        for n in (1, 10, 180, 1000):
            for c in (0.90, 0.95, 0.99):
                self.assertAlmostEqual(e.upper_bound(0, n, c), 1 - (1 - c) ** (1 / n), delta=1e-9)
            self.assertEqual(e.lower_bound(0, n), 0.0)

    def test_the_upper_bound_covers_the_true_fraction(self):
        # Over every possible soak of 180 intervals with a true fraction of 1%, the bound falls
        # below the truth with a probability of at most 5%. Counts above 40 have a probability
        # below 1e-15 at these fractions.
        for p in (0.003, 0.01, 0.03):
            miss = sum(pmf(k, 180, p) for k in range(41) if e.upper_bound(k, 180) < p)
            self.assertLessEqual(miss, 0.05, p)

    def test_the_lower_bound_covers_the_true_fraction(self):
        for p in (0.01, 0.05):
            miss = sum(pmf(k, 180, p) for k in range(41) if e.lower_bound(k, 180) > p)
            self.assertLessEqual(miss, 0.05, p)

    def test_a_long_soak_does_not_overflow(self):
        hi, lo = e.upper_bound(900, 100_000), e.lower_bound(900, 100_000)
        self.assertTrue(0.0085 < lo < 0.009 < hi < 0.0096, (lo, hi))

    def test_impossible_counts_are_refused(self):
        for k, n, c in ((5, 4, 0.95), (0, 0, 0.95), (-1, 10, 0.95), (1, 10, 1.0)):
            with self.assertRaises(ValueError):
                e.upper_bound(k, n, c)


class Soak(unittest.TestCase):
    def test_how_many_intervals_show_one_percent(self):
        self.assertEqual(e.intervals_needed(0.01), 299)
        self.assertEqual(e.intervals_needed(0.01, allowed=1), 473)
        self.assertEqual(e.intervals_needed(0.01, confidence=0.99), 459)

    def test_the_verdicts(self):
        self.assertEqual(e.verdict(0, 180, 0.01), "INCONCLUSIVE")
        self.assertEqual(e.verdict(1, 180, 0.01), "INCONCLUSIVE")
        self.assertEqual(e.verdict(15, 180, 0.01), "EXCEEDED")
        self.assertEqual(e.verdict(0, 300, 0.01), "DEMONSTRATED")
        self.assertEqual(e.verdict(5, 1000, 0.01), "INCONCLUSIVE")
        self.assertEqual(e.verdict(0, 1, 0.01), "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
