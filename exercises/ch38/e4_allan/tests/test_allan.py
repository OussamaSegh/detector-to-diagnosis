# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 38.4, on clocks whose Allan deviation is known."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import allan as a

TAU0 = 0.5  # one time error per monitor interval, as in Chapter 38
N = 20_000


def times():
    return np.arange(N) * TAU0


class Deterministic(unittest.TestCase):
    def test_an_offset_and_a_constant_frequency_have_none(self):
        x = 300e-12 + 1e-10 * times()  # 300 ps off and 0.1 ppb fast
        for m in (1, 3, 64):
            tau, dev, n = a.adev(x, TAU0, m)
            self.assertEqual((tau, n), (m * TAU0, N - 2 * m))
            self.assertLess(dev, 1e-18, m)

    def test_a_linear_frequency_drift_gives_d_tau_over_root_2(self):
        drift = 1e-13  # per second
        x = 0.5 * drift * times() ** 2
        for m in (1, 8, 1000):
            tau, dev, _ = a.adev(x, TAU0, m)
            self.assertAlmostEqual(dev / (drift * tau / np.sqrt(2)), 1.0, delta=1e-6, msg=m)


class Noise(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(38)

    def test_white_phase_noise(self):
        sigma = 26e-12  # the monitor's 26 ps per interval
        x = self.rng.normal(0.0, sigma, N)
        for m in (1, 10, 100):
            tau, dev, _ = a.adev(x, TAU0, m)
            self.assertAlmostEqual(dev / (np.sqrt(3) * sigma / tau), 1.0, delta=0.05, msg=m)
        self.assertAlmostEqual(a.slope(a.curve(x, TAU0)), -1.0, delta=0.05)

    def test_white_frequency_noise(self):
        sigma_y = 1e-11
        x = np.concatenate([[0.0], np.cumsum(self.rng.normal(0.0, sigma_y, N - 1)) * TAU0])
        for m in (1, 16):
            _, dev, _ = a.adev(x, TAU0, m)
            self.assertAlmostEqual(dev / (sigma_y / np.sqrt(m)), 1.0, delta=0.08, msg=m)
        self.assertAlmostEqual(a.slope(a.curve(x, TAU0)), -0.5, delta=0.1)

    def test_too_few_samples_are_refused(self):
        x = np.zeros(9)
        a.adev(x, TAU0, 4)
        for m in (5, 0, 2.0):
            with self.assertRaises(ValueError, msg=m):
                a.adev(x, TAU0, m)
        with self.assertRaises(ValueError):
            a.adev(x, 0.0, 1)


if __name__ == "__main__":
    unittest.main()
