# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 30.2."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import regions as r

N, PIXEL = 128, 1.0
C = (np.arange(N) - (N - 1) / 2.0) * PIXEL
XS, YS = np.meshgrid(C, C, indexing="xy")
CENTERS = [(40.0 * np.cos(a), 40.0 * np.sin(a)) for a in np.arange(12) * np.pi / 6]


class Contrast(unittest.TestCase):
    def test_the_true_contrast_is_one_and_none_is_zero(self):
        self.assertAlmostEqual(r.contrast_recovery(4.0, 1.0, 4.0), 1.0)
        self.assertAlmostEqual(r.contrast_recovery(8.0, 2.0, 4.0), 1.0)
        self.assertAlmostEqual(r.contrast_recovery(2.0, 2.0, 4.0), 0.0)
        self.assertAlmostEqual(r.contrast_recovery(2.5, 1.0, 4.0), 0.5)


class Variability(unittest.TestCase):
    def test_it_is_the_spread_of_the_regions_means(self):
        # Each region is uniform at its own level: the pixels do not vary inside a region, the
        # regions do, by a known amount.
        levels = 10.0 + np.array([1, -1, 2, -2, 0, 0, 1, -1, 3, -3, 0, 0], dtype=float)
        image = np.full((N, N), 10.0)
        for (cx, cy), v in zip(CENTERS, levels):
            image[r.disc(XS, YS, cx, cy, 6.0)] = v
        mean, var = r.background_variability(image, XS, YS, CENTERS, 6.0)
        self.assertAlmostEqual(mean, 10.0, places=12)
        self.assertAlmostEqual(var, np.std(levels, ddof=1) / 10.0, places=12)

    def test_white_noise_averages_down_with_the_region(self):
        # Independent pixel noise: a region's mean varies as 1 / sqrt(its pixels), so a region
        # of twice the radius varies half as much, and the pixels' own spread is not the answer.
        rng = np.random.default_rng(3)
        sd = []
        for radius in (3.0, 6.0):
            v = [r.background_variability(10.0 + rng.normal(0.0, 1.0, (N, N)), XS, YS, CENTERS,
                                          radius)[1] for _ in range(40)]
            sd.append(np.sqrt(np.mean(np.square(v))))
        pixels = [r.disc(XS, YS, 0.0, 0.0, radius).sum() for radius in (3.0, 6.0)]
        for s, n in zip(sd, pixels):
            self.assertAlmostEqual(s / (0.1 / np.sqrt(n)), 1.0, delta=0.1)
        self.assertAlmostEqual(sd[0] / sd[1], 2.0, delta=0.25)


if __name__ == "__main__":
    unittest.main()
