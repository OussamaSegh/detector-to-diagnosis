# SPDX-License-Identifier: MIT
import unittest

import energy_window as ew


class EnergyWindow(unittest.TestCase):
    def test_sigma(self):
        self.assertAlmostEqual(ew.sigma_kev(0.10), 21.70, delta=0.01)

    def test_photopeak_fraction(self):
        self.assertGreater(ew.photopeak_fraction(450.0, 613.0, 0.10), 0.99)
        self.assertAlmostEqual(ew.photopeak_fraction(0.0, 511.0, 0.10), 0.5, delta=0.001)
        self.assertLess(ew.photopeak_fraction(500.0, 520.0, 0.10), 0.5)

    def test_compton(self):
        self.assertAlmostEqual(ew.scattered_energy_kev(0.0), 511.0, delta=0.01)
        self.assertAlmostEqual(ew.scattered_energy_kev(90.0), 255.5, delta=0.01)
        self.assertAlmostEqual(ew.scattered_energy_kev(180.0), 170.33, delta=0.01)

    def test_min_rejected_angle(self):
        self.assertAlmostEqual(ew.min_rejected_angle_deg(450.0), 30.2, delta=0.1)
        self.assertAlmostEqual(ew.scattered_energy_kev(ew.min_rejected_angle_deg(400.0)), 400.0, delta=0.01)

    def test_window(self):
        for res in (0.10, 0.15):
            lo, hi = ew.choose_window(res)
            with self.subTest(resolution=res):
                self.assertGreaterEqual(lo, 425.0)
                self.assertLessEqual(hi, 650.0)
                self.assertLess(lo, 511.0)
                self.assertGreater(hi, 511.0)
                self.assertGreaterEqual(ew.photopeak_fraction(lo, hi, res), 0.95)


if __name__ == "__main__":
    unittest.main()
