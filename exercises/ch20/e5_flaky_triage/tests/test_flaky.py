# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 20.5. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import math
import unittest

import flaky as f


class Interval(unittest.TestCase):
    def test_no_failure_in_ten_runs(self):
        # Upper end: (1 - u)^10 = 0.025, u = 1 - 0.025^(1/10) = 0.30850.
        lo, hi = f.failure_rate_interval(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.025 ** 0.1, places=5)

    def test_eight_failures_in_eight_runs(self):
        # MDQ-PR-019 under load: l^8 = 0.025, l = 0.63096.
        lo, hi = f.failure_rate_interval(8, 8)
        self.assertAlmostEqual(lo, 0.025 ** (1 / 8), places=5)
        self.assertEqual(hi, 1.0)

    def test_the_interval_holds_the_observed_rate_and_shrinks_with_runs(self):
        lo10, hi10 = f.failure_rate_interval(3, 10)
        lo100, hi100 = f.failure_rate_interval(30, 100)
        self.assertTrue(lo10 < 0.3 < hi10 and lo100 < 0.3 < hi100)
        self.assertLess(hi100 - lo100, hi10 - lo10)

    def test_nonsense_is_refused(self):
        for args in [(1, 0), (-1, 5), (6, 5), (1, 5, 1.0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                f.failure_rate_interval(*args)


class Reruns(unittest.TestCase):
    def test_below_one_percent_with_95_percent_confidence(self):
        self.assertEqual(f.runs_needed(0.01, 0.95), 299)

    def test_the_answer_agrees_with_the_interval(self):
        n = f.runs_needed(0.05, 0.9)
        # The one-sided 90% bound is the upper end of the two-sided 80% interval.
        self.assertLess(f.failure_rate_interval(0, n, 0.8)[1], 0.05)
        self.assertGreaterEqual(f.failure_rate_interval(0, n - 1, 0.8)[1], 0.05)


class Change(unittest.TestCase):
    def test_mdq_pr_019(self):
        # 0 of 8 failed after the correction, 8 of 8 before: read backwards, "after" is worse.
        self.assertAlmostEqual(f.worse_after(0, 8, 8, 8), 1 / math.comb(16, 8), places=12)

    def test_no_change_is_not_significant(self):
        self.assertGreater(f.worse_after(2, 20, 2, 20), 0.5)

    def test_one_failure_in_a_few_runs_proves_little(self):
        self.assertGreater(f.worse_after(0, 5, 1, 5), 0.4)


class Retries(unittest.TestCase):
    def test_two_retries_hide_a_test_that_fails_30_percent(self):
        self.assertAlmostEqual(f.retries_hide(0.3, 2), 0.973, places=6)

    def test_retries_never_hide_a_test_that_always_fails(self):
        self.assertEqual(f.retries_hide(1.0, 5), 0.0)

    def test_no_retry_is_the_plain_pass_rate(self):
        self.assertAlmostEqual(f.retries_hide(0.25, 0), 0.75)


if __name__ == "__main__":
    unittest.main()
