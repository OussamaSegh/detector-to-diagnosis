# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 20.4. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this). The gate of Chapter 5
(tools/perf_gate.py) is put on the path first, so that `import perf_gate` works in ab.py."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))

import ab  # noqa: E402


class Schedule(unittest.TestCase):
    def test_interleaved_rounds_alternate_their_order(self):
        self.assertEqual(ab.schedule(3), ["A", "B", "B", "A", "A", "B"])

    def test_sequential_runs_all_a_first(self):
        self.assertEqual(ab.schedule(2, interleave=False), ["A", "A", "B", "B"])

    def test_no_round_is_refused(self):
        with self.assertRaises(ValueError):
            ab.schedule(0)


class Decide(unittest.TestCase):
    def test_a_clear_regression_and_none(self):
        a = [100.0, 101, 99, 100.5, 99.5]
        self.assertTrue(ab.decide(a, [90.0, 91, 89, 90.5, 89.5]))
        self.assertFalse(ab.decide(a, [99.0, 100, 101, 100.2, 99.8]))

    def test_a_small_but_certain_slowdown_is_not_a_regression(self):
        a = [100.0, 100.1, 100.2, 100.3, 100.4]
        self.assertFalse(ab.decide(a, [97.0, 97.1, 97.2, 97.3, 97.4]))


class Drift(unittest.TestCase):
    """The machine slows down or speeds up by 2% per run over the job (thermal, a neighbor)."""

    def test_running_a_then_b_turns_drift_into_a_false_alarm(self):
        self.assertGreaterEqual(ab.alarm_rate(10, False, ratio=1.0, drift=-0.02), 0.9)

    def test_running_a_then_b_hides_a_real_regression_behind_drift(self):
        self.assertLessEqual(ab.alarm_rate(10, False, ratio=0.9, drift=+0.02), 0.1)

    def test_interleaving_removes_the_false_alarm(self):
        self.assertLessEqual(ab.alarm_rate(10, True, ratio=1.0, drift=-0.02), 0.02)

    def test_but_unpaired_it_still_misses_the_regression(self):
        self.assertLessEqual(ab.alarm_rate(10, True, ratio=0.9, drift=+0.02), 0.2)


class Paired(unittest.TestCase):
    def test_round_ratios_follow_the_order(self):
        order = ["A", "B", "B", "A"]
        runs = {"A": [10.0, 20.0], "B": [9.0, 18.0]}
        self.assertEqual(ab.round_ratios(order, runs), [0.9, 0.9])

    def test_the_sign_test_of_five_rounds_cannot_go_below_one_in_32(self):
        self.assertAlmostEqual(ab.sign_test_p_less([0.9] * 5), 1 / 32)
        self.assertAlmostEqual(ab.sign_test_p_less([0.9] * 10), 1 / 1024)
        self.assertAlmostEqual(ab.sign_test_p_less([1.1] * 3), 1.0)

    def test_paired_rounds_find_the_regression_through_drift(self):
        self.assertGreaterEqual(ab.paired_alarm_rate(10, ratio=0.9, drift=+0.02), 0.95)
        self.assertLessEqual(ab.paired_alarm_rate(10, ratio=1.0, drift=-0.02), 0.02)

    def test_five_rounds_are_too_few_for_the_sign_test_at_alpha_0_01(self):
        self.assertEqual(ab.paired_alarm_rate(5, ratio=0.8, drift=0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
