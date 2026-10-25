# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 19.2. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this). The statistics module of
MiniDAQ's system tests is put on the path first, so that `import stats` works in power.py."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "minidaq/tests/system"))

import power  # noqa: E402


class MinimumDetectable(unittest.TestCase):
    def test_a_hand_computed_case(self):
        # n = 10000, alpha = 0.05, power = 0.5: z = 1.959964, k = 3.8415e-4, sqrt(k^2 + 8k) = 0.055436, r = 1.02791.
        self.assertAlmostEqual(power.min_detectable_ratio(10_000, 0.05, 0.5), 1.02791, places=4)

    def test_more_power_needs_a_larger_difference(self):
        r50 = power.min_detectable_ratio(10_000, 1e-3, 0.5)
        r90 = power.min_detectable_ratio(10_000, 1e-3, 0.9)
        self.assertGreater(r90, r50)

    def test_a_hundred_times_the_counts_sees_a_tenth_of_the_difference(self):
        small = power.min_detectable_ratio(10_000) - 1
        large = power.min_detectable_ratio(1_000_000) - 1
        self.assertAlmostEqual(small / large, 10, delta=0.3)

    def test_nonsense_is_refused(self):
        for args in ((0,), (100, 0.0), (100, 1e-3, 1.0)):
            with self.assertRaises(ValueError, msg=str(args)):
                power.min_detectable_ratio(*args)


class Simulated(unittest.TestCase):
    def test_without_a_difference_the_test_fails_at_about_alpha(self):
        p = power.simulated_power(150_000, 1.0, alpha=0.05, trials=2000, seed=3)
        self.assertLess(abs(p - 0.05), 0.015, p)

    def test_the_formula_agrees_with_the_simulation(self):
        n = 150_000
        r = power.min_detectable_ratio(n, 1e-3, 0.9)
        p = power.simulated_power(n, r, alpha=1e-3, trials=2000, seed=4)
        self.assertLess(abs(p - 0.9), 0.03, p)

    def test_power_grows_with_the_difference(self):
        ps = [power.simulated_power(150_000, r, alpha=1e-3, trials=500, seed=5) for r in (1.0, 1.01, 1.02, 1.04)]
        self.assertEqual(ps, sorted(ps), ps)
        self.assertGreater(ps[-1], 0.99)

    def test_small_counts_use_the_exact_test(self):
        # 40 counts: the exact test is conservative, so it fails less often than alpha.
        p = power.simulated_power(40, 1.0, alpha=0.05, trials=2000, seed=6)
        self.assertLess(p, 0.065, p)


class Golden(unittest.TestCase):
    def test_the_report_of_the_golden_run(self):
        golden = json.loads((ROOT / "minidaq/tests/system/golden/seed1.json").read_text())
        r = power.report(golden)
        self.assertEqual(set(r), {"prompts", "delayed"})
        # About a million singles gave a few hundred thousand prompts but only a few thousand
        # delayed coincidences: the randoms comparison is an order of magnitude blinder.
        self.assertLess(r["prompts"], 2.0)
        self.assertGreater(r["delayed"], 10.0)
        self.assertAlmostEqual(r["prompts"], 100 * (power.min_detectable_ratio(golden["prompts"]) - 1), places=1)


if __name__ == "__main__":
    unittest.main()
