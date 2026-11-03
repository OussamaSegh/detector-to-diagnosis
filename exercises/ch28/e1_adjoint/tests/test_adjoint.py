# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 28.1."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import adjoint as a


def mlem(y, g, iterations, x0=None):
    x = np.ones((g["n"], g["n"])) if x0 is None else x0.copy()
    sens = a.sensitivity(g)
    out = []
    for _ in range(iterations):
        ybar = a.forward(x, g)
        x = x * a.back(np.where(ybar > 0, y / np.where(ybar > 0, ybar, 1), 0), g) / sens
        ybar = a.forward(x, g)
        out.append(float((y * np.log(np.where(ybar > 0, ybar, 1)) - ybar).sum()))
    return x, out


class Adjoint(unittest.TestCase):
    def setUp(self):
        self.g = a.geometry()

    def test_the_dot_product_test(self):
        rng = np.random.default_rng(1)
        for _ in range(5):
            x = rng.random((32, 32))
            y = rng.random((36, 41))
            lhs = (a.forward(x, self.g) * y).sum()
            rhs = (x * a.back(y, self.g)).sum()
            self.assertAlmostEqual(lhs / rhs, 1.0, delta=1e-12)

    def test_the_sensitivity_is_the_backprojection_of_the_model(self):
        mult = np.random.default_rng(2).uniform(0.2, 1.0, (36, 41))
        want = a.back(mult, self.g)
        self.assertLess(np.abs(a.sensitivity(self.g, mult) - want).max(), 1e-12)
        # A pixel near the corner leaves the field of view in some views.
        s = a.sensitivity(self.g)
        self.assertLess(s[0, 0], s[16, 16])

    def test_mlem_climbs_and_finds_a_disc(self):
        g = self.g
        disc = ((g["x"] ** 2 + g["y"] ** 2) <= 10.0 ** 2).astype(float)
        y = a.forward(disc, g)
        x, ll = mlem(y, g, 30)
        self.assertTrue(all(b >= a_ - 1e-9 * abs(a_) for a_, b in zip(ll, ll[1:])))
        inner = (g["x"] ** 2 + g["y"] ** 2) <= 7.0 ** 2
        self.assertAlmostEqual(x[inner].mean(), 1.0, delta=0.03)
        self.assertLess(x[(g["x"] ** 2 + g["y"] ** 2) >= 13.0 ** 2].max(), 0.05)

    def test_the_true_image_is_a_fixed_point(self):
        # Activity everywhere, corners included: noiseless data of the truth, started at the
        # truth, must stay there. A wrong sensitivity moves the pixels that leave the field.
        g = self.g
        truth = 1.0 + 0.5 * np.cos(g["x"] / 5.0)
        x, _ = mlem(a.forward(truth, g), g, 5, x0=truth)
        self.assertLess(np.abs(x - truth).max(), 1e-9)


if __name__ == "__main__":
    unittest.main()
