# SPDX-License-Identifier: MIT
import math
import random
import unittest

import randoms as r

TAU = 4e-9      # 4 ns, MiniDAQ's default window
DELAY = 100e-9  # MiniDAQ's default delayed-window offset


class RandomsEstimate(unittest.TestCase):
    def test_the_formula(self):
        # 1 M singles/s in each detector, 4 ns: 2 * 4e-9 * 1e12 = 8000 randoms/s.
        self.assertAlmostEqual(r.singles_rate_estimate(1e6, 1e6, TAU), 8000.0, delta=1e-6)
        self.assertAlmostEqual(r.singles_rate_estimate(2e6, 1e6, TAU), 16000.0, delta=1e-6)

    def test_counting_is_symmetric(self):
        # One pair each way round, one just outside, one exactly on the edge.
        t1 = [10e-9, 50e-9, 90e-9]
        t2 = [7e-9, 54e-9, 95e-9]
        self.assertEqual(r.count_pairs(t1, t2, TAU), 2)  # 3 ns before, 4 ns after; 5 ns is out
        self.assertEqual(r.count_pairs(t2, t1, TAU), 2)

    def test_uncorrelated_streams_match_the_formula(self):
        s1, s2, seconds = 1e6, 0.8e6, 0.5
        rng = random.Random(1)
        t1 = r.poisson_times(s1, seconds, rng)
        t2 = r.poisson_times(s2, seconds, rng)
        expected = r.singles_rate_estimate(len(t1) / seconds, len(t2) / seconds, TAU) * seconds
        got = r.count_pairs(t1, t2, TAU)
        self.assertLess(abs(got - expected), 4 * math.sqrt(expected), f"{got} pairs, {expected:.0f} expected")
        delayed = r.count_pairs(t1, t2, TAU, offset=DELAY)
        self.assertLess(abs(delayed - expected), 4 * math.sqrt(expected), "no correlation: delayed = prompt")

    def test_with_trues_both_estimates_find_the_randoms(self):
        seconds = 0.5
        t1, t2, trues = r.with_trues(1e6, 1e6, 2e5, seconds, jitter=0.2e-9, seed=2)
        prompts = r.count_pairs(t1, t2, TAU)
        delayed = r.count_pairs(t1, t2, TAU, offset=DELAY)
        from_singles = r.singles_rate_estimate(len(t1) / seconds, len(t2) / seconds, TAU) * seconds
        sigma = math.sqrt(prompts + delayed)
        # The prompts hold every true pair (0.2 ns jitter is far inside 4 ns) plus the randoms.
        self.assertLess(abs((prompts - delayed) - trues), 4 * sigma)
        self.assertLess(abs(delayed - from_singles), 4 * math.sqrt(from_singles))
        self.assertGreater(trues, 50 * math.sqrt(from_singles), "the trues stand far above the noise")


if __name__ == "__main__":
    unittest.main()
