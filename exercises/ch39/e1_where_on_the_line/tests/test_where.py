# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 39.1."""
import math
import random
import unittest

from where import C_MM_PER_PS, position, tof_bin

R = 156.0


def crystal(angle):
    return R * math.cos(angle), R * math.sin(angle)


def times(p, a, b, t0=1_000_000.0):
    """The arrival times at a and b of the two photons of an annihilation at p."""
    return (t0 + math.dist(p, a) / C_MM_PER_PS, t0 + math.dist(p, b) / C_MM_PER_PS)


class Position(unittest.TestCase):
    def test_a_point_is_found_from_its_two_arrival_times(self):
        rng = random.Random(39)
        for _ in range(200):
            r, phi = 140.0 * math.sqrt(rng.random()), rng.uniform(0, 2 * math.pi)
            p = (r * math.cos(phi), r * math.sin(phi))
            theta = rng.uniform(0, math.pi)   # a line through p at angle theta
            d = (math.cos(theta), math.sin(theta))
            # Where the line meets the ring: p + s d with |p + s d| = R.
            pd = p[0] * d[0] + p[1] * d[1]
            root = math.sqrt(pd * pd - (p[0] ** 2 + p[1] ** 2 - R * R))
            a = (p[0] + (-pd - root) * d[0], p[1] + (-pd - root) * d[1])
            b = (p[0] + (-pd + root) * d[0], p[1] + (-pd + root) * d[1])
            for one, other in ((a, b), (b, a)):   # whichever crystal is called a
                ta, tb = times(p, one, other)
                got = position(one, other, ta, tb)
                self.assertAlmostEqual(got[0], p[0], delta=1e-6)
                self.assertAlmostEqual(got[1], p[1], delta=1e-6)

    def test_equal_times_give_the_middle(self):
        a, b = crystal(0.3), crystal(2.9)
        got = position(a, b, 5000.0, 5000.0)
        self.assertAlmostEqual(got[0], (a[0] + b[0]) / 2, places=9)
        self.assertAlmostEqual(got[1], (a[1] + b[1]) / 2, places=9)

    def test_a_time_difference_beyond_the_line_is_clamped(self):
        a, b = crystal(0.0), crystal(math.pi)   # a diameter, 312 mm
        got = position(a, b, 0.0, 5000.0)       # a far earlier than the line allows
        self.assertAlmostEqual(got[0], a[0], places=9)
        self.assertAlmostEqual(got[1], a[1], places=9)


class Bins(unittest.TestCase):
    def test_odd_bins_are_centered_on_zero(self):
        self.assertEqual(tof_bin(0.0, 5, 100.0), 2)
        self.assertEqual(tof_bin(49.9, 5, 100.0), 2)
        self.assertEqual(tof_bin(50.0, 5, 100.0), 3)     # an edge goes to the bin above
        self.assertEqual(tof_bin(-50.0, 5, 100.0), 2)
        self.assertEqual(tof_bin(-50.1, 5, 100.0), 1)
        self.assertEqual(tof_bin(-250.0, 5, 100.0), 0)
        self.assertIsNone(tof_bin(250.0, 5, 100.0))
        self.assertIsNone(tof_bin(-250.1, 5, 100.0))

    def test_even_bins_have_an_edge_at_zero(self):
        self.assertEqual(tof_bin(0.0, 4, 100.0), 2)
        self.assertEqual(tof_bin(-0.1, 4, 100.0), 1)
        self.assertEqual(tof_bin(-200.0, 4, 100.0), 0)
        self.assertIsNone(tof_bin(200.0, 4, 100.0))


if __name__ == "__main__":
    unittest.main()
