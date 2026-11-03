# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 30.1."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import width as w

FWHM_PER_SIGMA = 2.0 * np.sqrt(2.0 * np.log(2.0))
FWTM_PER_SIGMA = 2.0 * np.sqrt(2.0 * np.log(10.0))


def gaussian(sigma, center, size=41):
    k = np.arange(size)
    return 7.0 * np.exp(-0.5 * ((k - center) / sigma) ** 2)


class Width(unittest.TestCase):
    def test_straight_sides_are_measured_exactly(self):
        # A symmetric top and straight sides between the samples: the parabola finds the top and
        # linear interpolation is exact, whatever the level.
        p = np.array([0, 0, 1, 3, 4, 5, 4, 3, 1, 0, 0], dtype=float)
        self.assertAlmostEqual(w.width(p, 1.0, 0.5), 7.25 - 2.75, places=12)
        self.assertAlmostEqual(w.width(p, 1.0, 0.1), 8.5 - 1.5, places=12)
        self.assertAlmostEqual(w.width(p, 0.5, 0.5), 2.25, places=12)

    def test_a_gaussian_wherever_it_falls_between_samples(self):
        # sigma of 1.5 samples is a FWHM of 3.5 samples, near NEMA's three pixels per FWHM;
        # linear interpolation across a curved side overestimates the width a little. With
        # twice the samples, much less.
        for sigma, tolerance in ((1.5, 0.04), (3.0, 0.015)):
            for center in (20.0, 20.25, 20.5, 20.75):
                p = gaussian(sigma, center)
                self.assertAlmostEqual(w.width(p, 2.0) / (2.0 * sigma * FWHM_PER_SIGMA), 1.0,
                                       delta=tolerance)
                self.assertAlmostEqual(w.width(p, 2.0, 0.1) / (2.0 * sigma * FWTM_PER_SIGMA),
                                       1.0, delta=tolerance)

    def test_the_peak_is_between_the_samples(self):
        p = gaussian(1.5, 20.5)
        position, value = w.peak(p)
        self.assertAlmostEqual(position, 20.5, places=9)
        self.assertAlmostEqual(value, 7.0, delta=0.14)

    def test_a_profile_cut_off_is_refused(self):
        with self.assertRaises(ValueError):
            w.width(gaussian(1.5, 1.0, size=12), 1.0)
        with self.assertRaises(ValueError):
            w.width(np.ones(9), 1.0)


if __name__ == "__main__":
    unittest.main()
