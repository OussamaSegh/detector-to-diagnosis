# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 39.4, on the cylinder of Chapter 39 (radius 100 mm)."""
import math
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import gain as g

R = 100.0


class Gain(unittest.TestCase):
    def test_the_localization_is_c_over_two_times_the_resolution(self):
        self.assertAlmostEqual(g.localization_mm(300), 44.969, places=3)
        for bad in (0, -300):
            with self.assertRaises(ValueError):
                g.localization_mm(bad)

    def test_chords(self):
        self.assertAlmostEqual(float(g.chord_mm(0.0, 1.0, R)), 200.0)
        self.assertAlmostEqual(float(g.chord_mm(60.0, 0.0, R)), 200.0)
        self.assertAlmostEqual(float(g.chord_mm(60.0, math.pi / 2, R)), 160.0)
        with self.assertRaises(ValueError):
            g.chord_mm(101.0, 0.0, R)

    def test_at_the_center_it_is_the_usual_estimate(self):
        self.assertAlmostEqual(g.gain(0.0, R, 300), math.sqrt(200 / 44.969), delta=1e-3)
        self.assertAlmostEqual(g.gain(0.0, R, 500), math.sqrt(200 / 74.948), delta=1e-3)

    def test_the_gain_falls_away_from_the_center(self):
        at = [g.gain(r, R, 300) for r in (0.0, 30.0, 55.0, 90.0, 99.9)]
        self.assertTrue(all(a > b for a, b in zip(at, at[1:])), at)
        self.assertAlmostEqual(at[2], 2.022, delta=0.005)

    def test_an_object_smaller_than_the_localization_gains_nothing(self):
        self.assertAlmostEqual(g.gain(0.0, 10.0, 300), 1.0, delta=1e-12)
        self.assertAlmostEqual(g.gain(5.0, 10.0, 500), 1.0, delta=1e-12)

    def test_regions_add_their_variances(self):
        self.assertAlmostEqual(g.region_gain([(0.0, 0.0)], R, 300), g.gain(0.0, R, 300))
        pts = [(0.0, 0.0), (0.0, 95.0)]
        a, b = g.gain(0.0, R, 300), g.gain(95.0, R, 300)
        self.assertAlmostEqual(g.region_gain(pts, R, 300), 1 / math.sqrt((a ** -2 + b ** -2) / 2),
                               delta=1e-9)
        # The 15 regions of measurements/ch39/tof.py.
        centers = [(r * math.cos(t), r * math.sin(t)) for r in (30.0, 55.0)
                   for t in np.arange(8) * math.pi / 4]
        regions = [(0.0, 0.0)] + [c for c in centers if math.hypot(c[0] - 50, c[1]) > 28]
        self.assertEqual(len(regions), 15)
        self.assertAlmostEqual(g.region_gain(regions, R, 300), 2.056, delta=0.005)
        with self.assertRaises(ValueError):
            g.region_gain([], R, 300)


if __name__ == "__main__":
    unittest.main()
