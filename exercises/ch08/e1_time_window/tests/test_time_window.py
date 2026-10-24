# SPDX-License-Identifier: MIT
import unittest

import time_window as tw


class TimeWindow(unittest.TestCase):
    def test_full_ring(self):
        self.assertAlmostEqual(tw.max_time_difference_ps(300.0), 1000.69, delta=0.1)

    def test_field_of_view(self):
        self.assertAlmostEqual(tw.max_time_difference_ps(200.0),
                               tw.max_time_difference_ps(300.0) * 2.0 / 3.0, delta=0.01)

    def test_window_with_timing_resolution(self):
        self.assertAlmostEqual(tw.prompt_window_ps(300.0, 300.0, 3.0), 2765.6, delta=1.0)
        self.assertAlmostEqual(tw.prompt_window_ps(300.0, 0.0, 3.0), 2001.4, delta=1.0)

    def test_fraction_kept(self):
        self.assertAlmostEqual(tw.true_fraction_kept(1000.0, 1000.0, 300.0), 0.5, delta=0.001)
        sigma = 300.0 / 2.3548
        self.assertGreater(tw.true_fraction_kept(1000.0 + 3 * sigma, 1000.0, 300.0), 0.998)
        self.assertLess(tw.true_fraction_kept(1000.0, 1300.0, 300.0), 0.02)
        self.assertEqual(tw.true_fraction_kept(1000.0, 999.0, 0.0), 1.0)


if __name__ == "__main__":
    unittest.main()
