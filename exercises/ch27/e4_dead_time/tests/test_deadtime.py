# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 27.4, on the recorded rates of a synthetic decaying source."""
import math
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import deadtime as d

TAU = 200e-9          # s
HALF_LIFE = 109.77    # min, fluorine-18
N0 = 3.0e6            # true events per second at t = 0


def series(kind, seed=27, seconds=10.0):
    """Recorded rates every 20 minutes for 10 hours, each counted for `seconds`."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, 600.0, 20.0)
    n = N0 * np.exp(-math.log(2.0) / HALF_LIFE * t)
    m = d.recorded_rate(n, TAU, kind)
    return t, rng.poisson(m * seconds) / seconds


class Inversion(unittest.TestCase):
    def test_true_rate_inverts_each_model(self):
        n = np.geomspace(1e3, 0.9 / TAU, 50)  # up to 0.9 / tau: the paralyzable lower branch
        for kind in d.KINDS:
            got = d.true_rate(d.recorded_rate(n, TAU, kind), TAU, kind)
            self.assertTrue(np.allclose(got, n, rtol=1e-9), kind)

    def test_a_paralyzable_rate_above_its_maximum_is_refused(self):
        top = 1.0 / (math.e * TAU)
        self.assertAlmostEqual(float(d.recorded_rate(1.0 / TAU, TAU, "paralyzable")), top,
                               delta=1e-9 * top)
        with self.assertRaises(ValueError):
            d.true_rate(1.01 * top, TAU, "paralyzable")
        with self.assertRaises(ValueError):
            d.true_rate(1.0 / TAU, TAU, "nonparalyzable")

    def test_the_kinds_differ_where_it_matters(self):
        m = d.recorded_rate(N0, TAU, "paralyzable")  # 1.65 M recorded of 3 M
        self.assertAlmostEqual(float(d.true_rate(m, TAU, "paralyzable")), N0, delta=1.0)
        self.assertLess(float(d.true_rate(m, TAU, "nonparalyzable")), 0.9 * N0)


class Fit(unittest.TestCase):
    def test_a_paralyzable_unit_is_recognized(self):
        t, m = series("paralyzable")
        f = d.fit(t, m, HALF_LIFE)
        self.assertEqual(f["kind"], "paralyzable")
        tau, n0, spread = f["paralyzable"]
        self.assertLess(abs(tau / TAU - 1.0), 0.02)
        self.assertLess(abs(n0 / N0 - 1.0), 0.005)
        self.assertLess(spread, 0.005)
        self.assertGreater(f["nonparalyzable"][2], 3 * spread)

    def test_a_nonparalyzable_unit_is_recognized(self):
        t, m = series("nonparalyzable", seed=28)
        f = d.fit(t, m, HALF_LIFE)
        self.assertEqual(f["kind"], "nonparalyzable")
        tau, n0, _ = f["nonparalyzable"]
        self.assertLess(abs(tau / TAU - 1.0), 0.02)
        self.assertLess(abs(n0 / N0 - 1.0), 0.005)

    def test_the_fit_does_not_depend_on_the_last_point(self):
        t, m = series("paralyzable", seed=29, seconds=1.0)
        m[-1] *= 1.05  # a weak last point, 5% off
        tau, n0, _ = d.fit(t, m, HALF_LIFE)["paralyzable"]
        self.assertLess(abs(tau / TAU - 1.0), 0.03)
        self.assertLess(abs(n0 / N0 - 1.0), 0.01)


if __name__ == "__main__":
    unittest.main()
