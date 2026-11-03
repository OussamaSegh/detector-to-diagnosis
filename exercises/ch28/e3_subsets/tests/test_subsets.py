# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 28.3."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import projector
import subsets as s


def mlem(y, p, mult, add, iterations):
    """The reference: MLEM with the corrections in the model (Exercise 28.2)."""
    sens = p.back(mult)
    x = np.ones((p.n, p.n))
    for _ in range(iterations):
        ybar = mult * p.forward(x) + add
        x = x * p.back(mult * y / ybar) / sens
    return x


class Subsets(unittest.TestCase):
    def setUp(self):
        self.p = projector.Projector()
        self.r2 = self.p.x ** 2 + self.p.y ** 2
        # The multiplicative factors change from view to view, as the attenuation of an ellipse
        # does.
        phi = np.arange(36) * np.pi / 36
        self.mult = (0.3 + 0.6 * np.abs(np.cos(phi)))[:, None] * np.ones((1, 41))

    def test_the_subsets_hold_every_view_once_and_span_the_half_turn(self):
        groups = s.subsets(36, 5)
        self.assertEqual(sorted(int(v) for g in groups for v in g), list(range(36)))
        sizes = [len(g) for g in groups]
        self.assertLessEqual(max(sizes) - min(sizes), 1)
        for g in groups:
            views = sorted(int(v) for v in g)
            # View 36 would be view 0 turned over: the gaps are counted around the half turn.
            # 36 views do not divide into 5, so one gap per subset may be 6.
            gaps = np.diff(views + [views[0] + 36])
            self.assertLessEqual(gaps.max(), 6)

    def test_impossible_subsets_are_refused(self):
        for count in (0, 37):
            with self.assertRaises(ValueError):
                s.subsets(36, count)

    def test_the_true_image_is_a_fixed_point(self):
        p, mult = self.p, self.mult
        truth = 1.0 + 0.5 * np.cos(p.x / 5.0)
        x = s.osem(mult * p.forward(truth), p, mult, 0.0, 3, 5, x0=truth)
        self.assertLess(np.abs(x - truth).max(), 1e-9)

    def test_four_iterations_of_five_subsets_are_twenty_of_mlem(self):
        p, mult, r2 = self.p, self.mult, self.r2
        image = (np.where(r2 <= 14 ** 2, 1.0, 0.0)
                 + np.where((p.x - 6) ** 2 + p.y ** 2 <= 3 ** 2, 3.0, 0.0))
        for scale, add, rng in ((1.0, 0.2, None), (10.0, 2.0, np.random.default_rng(7))):
            mean = scale * mult * p.forward(image) + add
            y = mean if rng is None else rng.poisson(mean).astype(float)
            ref = mlem(y, p, scale * mult, add, 20)
            x = s.osem(y, p, scale * mult, add, 4, 5)
            rms = np.sqrt(((x - ref) ** 2).mean()) / ref[r2 <= 14 ** 2].mean()
            self.assertLess(rms, 0.03)
            self.assertAlmostEqual(x.sum() / ref.sum(), 1.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
