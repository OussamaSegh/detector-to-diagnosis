# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 26.4, on the peak codes of synthetic crystals."""
import math
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import second_line as s

E_SAT = 1500.0  # the sensor's, as measurements/ch26 uses


def codes(gains, e_sat=E_SAT, line=s.LINE_KEV):
    """The codes of the 511 keV photopeak and of the line, for each gain."""
    g = np.asarray(gains, dtype=float)
    return (g * s.saturate(s.PEAK_KEV, e_sat) / s.ENERGY_LSB_KEV,
            g * s.saturate(line, e_sat) / s.ENERGY_LSB_KEV)


class SecondLine(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(26)
        self.gains = rng.normal(1.0, 0.1, 40)
        self.c511, self.cline = codes(self.gains)

    def test_the_curve_puts_each_line_at_its_energy(self):
        self.assertTrue(np.allclose(s.energy_of(self.c511, self.c511, E_SAT), 511.0, rtol=1e-12))
        self.assertTrue(np.allclose(s.energy_of(self.cline, self.c511, E_SAT), 307.0, rtol=1e-9))

    def test_the_right_e_sat_passes(self):
        ok, found, worst = s.check_e_sat(E_SAT, self.c511, self.cline)
        self.assertTrue(ok, worst)
        self.assertEqual(found.shape, (40,))
        # And with the peak centers' statistical error, 0.2% each:
        rng = np.random.default_rng(1)
        ok, _, worst = s.check_e_sat(E_SAT, self.c511 * rng.normal(1, 0.002, 40),
                                     self.cline * rng.normal(1, 0.002, 40))
        self.assertTrue(ok, worst)

    def test_a_wrong_e_sat_is_refused(self):
        # Every one of these puts every photopeak at 511 keV exactly.
        for wrong in (1200.0, 1800.0, 3000.0, math.inf):
            ok, _, worst = s.check_e_sat(wrong, self.c511, self.cline)
            self.assertFalse(ok, f"E_sat {wrong} accepted")
            self.assertGreater(worst, 0.008)
            self.assertTrue(np.allclose(s.energy_of(self.c511, self.c511, wrong), 511.0))
        self.assertLess(s.check_e_sat(1200.0, self.c511, self.cline)[1].mean(), 303.0)
        self.assertGreater(s.check_e_sat(1800.0, self.c511, self.cline)[1].mean(), 309.0)

    def test_e_sat_is_found_from_the_two_peaks(self):
        for e_sat in (900.0, 1500.0, 2500.0):
            c511, cline = codes([1.0], e_sat)
            self.assertAlmostEqual(s.estimate_e_sat(c511[0], cline[0]), e_sat, delta=1e-6 * e_sat)
        # 40 crystals, peak centers to 0.2%: each estimate is rough, their median is not.
        rng = np.random.default_rng(2)
        est = [s.estimate_e_sat(a * rng.normal(1, 0.002), b * rng.normal(1, 0.002))
               for a, b in zip(self.c511, self.cline)]
        finite = np.array([e for e in est if math.isfinite(e)])
        self.assertGreater(finite.size, 30)
        self.assertLess(abs(np.median(finite) / E_SAT - 1.0), 0.1)

    def test_a_linear_detector_has_no_finite_e_sat(self):
        c511, cline = codes([1.0, 1.2], math.inf)
        self.assertEqual(s.estimate_e_sat(c511[0], cline[0]), math.inf)
        self.assertEqual(s.estimate_e_sat(c511[1] * 1.001, cline[1]), math.inf)  # noise above
        self.assertTrue(s.check_e_sat(math.inf, c511, cline)[0])


if __name__ == "__main__":
    unittest.main()
