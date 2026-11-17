# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 28.4, on a noisy disc with a hot rod in 36 views."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import ordered
import projector
import stopping as s

TARGET = 0.20


class Stopping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = projector.Projector()
        r2 = p.x ** 2 + p.y ** 2
        rod2 = (p.x - 6) ** 2 + p.y ** 2
        phi = np.arange(36) * np.pi / 36
        cls.mult = 5.0 * (0.3 + 0.6 * np.abs(np.cos(phi)))[:, None] * np.ones((1, 41))
        image = np.where(r2 <= 14 ** 2, 1.0, 0.0) + np.where(rod2 <= 3 ** 2, 3.0, 0.0)
        mean = cls.mult * p.forward(image) + 1.0
        cls.y = np.random.default_rng(11).poisson(mean).astype(float)
        cls.p = p
        cls.background = (r2 <= 10 ** 2) & (rod2 > 5 ** 2)
        cls.rod = rod2 <= 2 ** 2

    def run_(self, count, target=TARGET):
        return s.stop(self.y, self.p, self.mult, 1.0, count, target, self.background)

    def cov(self, x):
        v = x[self.background]
        return v.std() / v.mean()

    def crc(self, x):
        return (x[self.rod].mean() / x[self.background].mean() - 1.0) / 3.0

    def test_it_stops_at_the_last_iteration_below_the_target(self):
        it, x, noise = self.run_(4)
        self.assertLessEqual(noise, TARGET)
        again = ordered.osem(self.y, self.p, self.mult, 1.0, it, 4)
        self.assertTrue(np.allclose(again, x, rtol=1e-12, atol=0))
        one_more = ordered.osem(self.y, self.p, self.mult, 1.0, it + 1, 4)
        self.assertGreater(self.cov(one_more), TARGET)

    def test_the_noise_is_that_of_the_background(self):
        it, x, noise = self.run_(2)
        self.assertAlmostEqual(noise, self.cov(x), delta=1e-12)
        self.assertGreater(it, 1)

    def test_at_the_same_noise_fair_subsets_give_the_same_image(self):
        it1, x1, _ = self.run_(1)
        for count in (2, 3, 6):
            # 6 subsets can stop only every 6 updates: one stop fewer than MLEM here.
            it, x, noise = self.run_(count)
            self.assertLessEqual(abs(it * count - it1), count, count)
            self.assertAlmostEqual(self.crc(x), self.crc(x1), delta=0.03, msg=count)
            self.assertLessEqual(noise, TARGET, count)

    def test_subsets_too_small_are_refused(self):
        with self.assertRaises(ValueError):
            self.run_(12)  # 3 views in a subset
        with self.assertRaises(ValueError):
            self.run_(0)

    def test_a_target_below_the_first_iteration_is_refused(self):
        with self.assertRaises(ValueError):
            self.run_(6, target=0.05)


if __name__ == "__main__":
    unittest.main()
