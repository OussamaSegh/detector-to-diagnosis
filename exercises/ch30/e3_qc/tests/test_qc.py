# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 30.3."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import qc

# Six acceptance results of a rod's contrast recovery: mean 1.00, sample SD 0.018.
BASELINE = [0.98, 1.02, 1.00, 0.98, 1.02, 1.00]
SD = float(np.std(BASELINE, ddof=1))


class Limits(unittest.TestCase):
    def test_three_sample_standard_deviations(self):
        low, high = qc.limits(BASELINE)
        self.assertAlmostEqual(low, 1.0 - 3 * SD, places=12)
        self.assertAlmostEqual(high, 1.0 + 3 * SD, places=12)

    def test_too_small_a_baseline_is_refused(self):
        with self.assertRaises(ValueError):
            qc.limits(BASELINE[:4])


class Review(unittest.TestCase):
    def test_results_within_the_limits_and_around_the_mean_pass(self):
        results = [1.0 + d * SD for d in (0.5, -1.0, 2.0, -0.5, 1.5, -2.5, 0.0, 1.0, -1.0, 2.5)]
        self.assertEqual(qc.review(results, BASELINE), [])

    def test_one_result_outside_is_reported_where_it_is(self):
        results = [1.0, 1.0 + SD, 1.0 - 3.5 * SD, 1.0, 1.0 - SD]
        self.assertEqual(qc.review(results, BASELINE), [(2, "out")])

    def test_a_drift_does_not_widen_its_own_limits(self):
        # The contrast falls by 0.45 standard deviations a week: from week 7 on it is outside.
        results = [1.0 - 0.45 * SD * w for w in range(12)]
        out = [i for i, kind in qc.review(results, BASELINE) if kind == "out"]
        self.assertEqual(out, list(range(7, 12)))

    def test_a_small_shift_is_found_by_its_run(self):
        # One standard deviation down from week 3: never outside the limits, always below the
        # mean. The seventh result in a row below it is the finding.
        results = [1.0 + SD, 1.0 - 0.5 * SD, 1.0 + 0.5 * SD] + [1.0 - SD * (1 + 0.3 * (w % 2))
                                                               for w in range(10)]
        self.assertEqual(qc.review(results, BASELINE), [(9, "run")])


if __name__ == "__main__":
    unittest.main()
