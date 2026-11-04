# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 35.1."""
import unittest

import numpy as np

from ds import format_ds, quantize


class DecimalString(unittest.TestCase):
    def test_at_most_16_characters_and_precise(self):
        rng = np.random.default_rng(35)
        values = rng.normal(size=300) * 10.0 ** rng.integers(-12, 13, size=300)
        for x in list(values) + [-0.0, 1.0 / 3.0, 65535.0, 123456789012.345]:
            s = format_ds(x)
            self.assertLessEqual(len(s), 16, s)
            self.assertLessEqual(abs(float(s) - x), abs(x) * 5e-10, s)

    def test_a_small_slope_is_not_zero(self):
        self.assertAlmostEqual(float(format_ds(1.4335787263766564e-07)), 1.4335787263766564e-07,
                               delta=1e-17)

    def test_a_value_that_is_not_finite_is_refused(self):
        for x in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(x=x), self.assertRaises(ValueError):
                format_ds(x)


class Quantize(unittest.TestCase):
    def test_every_value_comes_back_within_half_the_written_slope(self):
        rng = np.random.default_rng(1)
        for peak in (0.0094, 1.0 / 3.0, 7.0e5, 3.3e-9):
            plane = rng.random((64, 64)) * peak
            stored, text = quantize(plane)
            self.assertEqual(stored.dtype, np.uint16)
            self.assertLessEqual(len(text), 16)
            slope = float(text)
            self.assertLessEqual(np.abs(stored * slope - plane).max(), slope / 2 * (1 + 1e-12))
            self.assertEqual(int(stored.max()), 65535)

    def test_an_empty_plane_has_a_slope_of_one(self):
        stored, text = quantize(np.zeros((4, 4)))
        self.assertEqual(float(text), 1.0)
        self.assertFalse(stored.any())


if __name__ == "__main__":
    unittest.main()
