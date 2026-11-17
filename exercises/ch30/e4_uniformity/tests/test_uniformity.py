# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 30.4, on images of a synthetic uniform cylinder."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import uniformity as u

N, CENTER, RADIUS = 128, (63.5, 63.5), 50.0


def cylinder(level=lambda x, y: np.ones_like(x)):
    """A cylinder of radius 50 pixels whose edge is blurred over 4 pixels, as the resolution
    blurs it; inside, the activity `level(x, y)`."""
    yy, xx = np.indices((N, N)).astype(float)
    r = np.hypot(xx - CENTER[0], yy - CENTER[1])
    edge = np.clip((RADIUS + 2.0 - r) / 4.0, 0.0, 1.0)
    return edge * level(xx - CENTER[0], yy - CENTER[1])


class Uniformity(unittest.TestCase):
    def setUp(self):
        self.cfov = u.central_region((N, N), CENTER, RADIUS)

    def test_the_kernel_smooths_and_keeps_the_level(self):
        flat = np.full((9, 9), 3.0)
        self.assertTrue(np.allclose(u.smooth(flat)[1:-1, 1:-1], 3.0))
        delta = np.zeros((5, 5))
        delta[2, 2] = 16.0
        self.assertTrue(np.allclose(u.smooth(delta)[1:4, 1:4], [[1, 2, 1], [2, 4, 2], [1, 2, 1]]))

    def test_a_uniform_cylinder_is_uniform(self):
        integral, differential = u.uniformity(cylinder(), self.cfov)
        self.assertLess(integral, 0.01)  # the blurred edge is not in the central field
        self.assertLess(differential, 0.01)

    def test_a_gradient_across_the_field(self):
        img = cylinder(lambda x, y: 1.0 + 0.05 * x / RADIUS)  # 5% from the center to the edge
        integral, differential = u.uniformity(img, self.cfov)
        self.assertGreater(integral, 3.4)  # 75% of the radius: about 3.7%
        self.assertLess(integral, 3.8)
        self.assertLess(differential, 0.3)

    def test_noise_is_smoothed_before_it_is_measured(self):
        rng = np.random.default_rng(30)
        img = cylinder() * rng.normal(1.0, 0.02, (N, N))  # 2% per pixel
        integral, differential = u.uniformity(img, self.cfov)
        self.assertLess(integral, 4.0)   # unsmoothed, the extremes of 4,000 pixels: about 7%
        self.assertLess(differential, 3.0)

    def test_a_cold_row_is_seen_along_the_columns(self):
        img = cylinder()
        img[64, :] *= 0.9  # one whole row 10% low: along the rows, nothing changes
        integral, differential = u.uniformity(img, self.cfov)
        self.assertGreater(differential, 2.0)  # 0.95 next to 1.0 after smoothing: 2.6%
        self.assertGreater(integral, 2.0)

    def test_a_region_too_small_is_refused(self):
        with self.assertRaises(ValueError):
            u.uniformity(cylinder(), u.central_region((N, N), CENTER, 4.0))


if __name__ == "__main__":
    unittest.main()
