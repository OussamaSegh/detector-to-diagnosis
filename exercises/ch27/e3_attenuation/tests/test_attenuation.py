# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 27.3."""
import math
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import attenuation as at


def marched(s, phi, a, b, center, angle, step=0.005):
    """A chord measured by walking along the line in steps of `step` mm."""
    n = np.array([math.cos(phi), math.sin(phi)])
    t = np.arange(-200.0, 200.0, step)
    p = s * n[:, None] + np.array([-n[1], n[0]])[:, None] * t[None, :]
    p -= np.asarray(center)[:, None]
    c, sn = math.cos(angle), math.sin(angle)
    x, y = c * p[0] + sn * p[1], -sn * p[0] + c * p[1]
    return step * np.count_nonzero((x / a) ** 2 + (y / b) ** 2 <= 1.0)


class Chords(unittest.TestCase):
    def test_a_circle(self):
        s = np.linspace(-120, 120, 49)
        got = at.chords(s, 0.3, 90.0, 90.0)
        self.assertTrue(np.allclose(got, 2 * np.sqrt(np.clip(90.0 ** 2 - s ** 2, 0, None))))

    def test_an_ellipse_off_center_and_turned(self):
        rng = np.random.default_rng(1)
        for _ in range(40):
            a, b = rng.uniform(60, 100, 2)
            center = rng.uniform(-20, 20, 2)
            angle, phi = rng.uniform(0, math.pi, 2)
            s = rng.uniform(-100, 100)
            want = marched(s, phi, a, b, center, angle)
            self.assertAlmostEqual(float(at.chords(s, phi, a, b, center, angle)), want, delta=0.05)

    def test_a_head_its_axes_and_its_tilt(self):
        # A head 160 mm wide and 200 mm long, turned 20 degrees: the line through its center
        # along its long axis is 200 mm, not the 180 mm of a circle of the mean radius. (A line
        # whose normal is the head's own x axis runs along its y axis.)
        a, b, tilt = 80.0, 100.0, math.radians(20)
        self.assertAlmostEqual(float(at.chords(0.0, tilt, a, b, (0, 0), tilt)), 200.0, places=6)
        self.assertAlmostEqual(float(at.chords(0.0, tilt + math.pi / 2, a, b, (0, 0), tilt)),
                               160.0, places=6)


class Factors(unittest.TestCase):
    def test_water(self):
        # 0.096 per cm through 200 mm of water: exp(1.92).
        self.assertAlmostEqual(float(at.acf(200.0)), math.exp(1.92), places=9)
        self.assertEqual(float(at.acf(0.0)), 1.0)

    def test_decay_of_a_frame(self):
        half = 6586.2  # fluorine-18, 109.77 min (verify: NIST and DDEP give 109.77 min)
        self.assertAlmostEqual(at.decay_factor(0.0, 1e-6, half), 1.0, places=6)
        self.assertAlmostEqual(at.decay_factor(half, 1e-6, half), 2.0, places=6)
        # A frame one half-life long: the mean activity is 1/(2 ln 2) of the start's.
        self.assertAlmostEqual(at.decay_factor(0.0, half, half), 2 * math.log(2), places=9)

    def test_frames_of_any_length_agree(self):
        # A constant activity at the reference time, imaged in frames of 60 s to 30 min: every
        # frame's counts, corrected, give the same activity.
        half, a0 = 6586.2, 1000.0
        lam = math.log(2) / half
        start = 0.0
        for length in (60.0, 300.0, 600.0, 1800.0):
            counts = a0 / lam * (math.exp(-lam * start) - math.exp(-lam * (start + length)))
            self.assertAlmostEqual(counts / length * at.decay_factor(start, length, half), a0,
                                   delta=1e-9 * a0)
            start += length


if __name__ == "__main__":
    unittest.main()
