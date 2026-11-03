# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 28.2."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import model
import projector


def climbs(history):
    return all(b >= a - 1e-9 * abs(a) for a, b in zip(history, history[1:]))


class Model(unittest.TestCase):
    def setUp(self):
        self.p = projector.Projector()
        self.r2 = self.p.x ** 2 + self.p.y ** 2

    def test_low_counts_and_many_randoms_are_unbiased(self):
        # About 1 true and 2 randoms per bin at most: the counts of a short frame. The mean of
        # 20 noise realizations, 100 iterations each.
        p, r2 = self.p, self.r2
        truth = np.where(r2 <= 12 ** 2, 0.1, 0.0)
        mult, add = np.full((36, 41), 0.5), np.full((36, 41), 2.0)
        rng = np.random.default_rng(5)
        mean = np.zeros_like(truth)
        for _ in range(20):
            y = rng.poisson(mult * p.forward(truth) + add)
            x, history = model.reconstruct(y, p, mult, add, 100)
            self.assertTrue(climbs(history))
            mean += x / 20
        self.assertAlmostEqual(mean[r2 <= 8 ** 2].mean() / 0.1, 1.0, delta=0.03)
        self.assertLess(mean[(r2 >= 15 ** 2) & (r2 <= 19 ** 2)].mean(), 0.04)

    def test_bins_in_the_gaps_are_not_zero_counts(self):
        # Every sixth radial bin is not measured (mult = 0) and records nothing.
        p, r2 = self.p, self.r2
        mult = np.ones((36, 41))
        mult[:, ::6] = 0.0
        truth = np.where(r2 <= 15 ** 2, 1.0, 0.0)
        x, history = model.reconstruct(mult * p.forward(truth), p, mult, 0.0, 50)
        self.assertTrue(climbs(history))
        inner = x[r2 <= 12 ** 2]
        self.assertAlmostEqual(inner.mean(), 1.0, delta=0.01)
        self.assertLess(inner.std(), 0.05)

    def test_the_measured_counts_are_left_alone(self):
        p = self.p
        y = np.random.default_rng(6).poisson(1.0, (36, 41)).astype(float)
        keep = y.copy()
        model.reconstruct(y, p, np.full((36, 41), 0.5), np.full((36, 41), 0.7), 2)
        self.assertTrue(np.array_equal(y, keep))


if __name__ == "__main__":
    unittest.main()
