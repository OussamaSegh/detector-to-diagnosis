# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 35.2."""
import unittest

import numpy as np

from plane import export_rows, plane, to_patient


def hot(rows, cols, row_mm, col_mm, x_mm, y_mm):
    """An image with one pixel at gantry (x_mm, y_mm); returns the image."""
    img = np.zeros((rows, cols))
    c = round(x_mm / col_mm + (cols - 1) / 2.0)
    r = round(y_mm / row_mm + (rows - 1) / 2.0)
    assert np.isclose((c - (cols - 1) / 2.0) * col_mm, x_mm)
    assert np.isclose((r - (rows - 1) / 2.0) * row_mm, y_mm)
    img[r, c] = 1.0
    return img


class Plane(unittest.TestCase):
    def check(self, position, rows, cols, row_mm, col_mm, expect):
        x, y, z = 19.0, 29.0, 12.0
        img = export_rows(hot(rows, cols, row_mm, col_mm, x, y))
        a = plane(img.shape, row_mm, col_mm, z, position)
        r, c = np.unravel_index(np.argmax(img), img.shape)
        p = to_patient(a["ImagePositionPatient"], a["ImageOrientationPatient"], a["PixelSpacing"],
                       r, c)
        self.assertTrue(np.allclose(p, expect(x, y, z)), (position, p, expect(x, y, z)))

    def test_head_first_with_square_pixels(self):
        self.check("HFS", 32, 32, 2.0, 2.0, lambda x, y, z: (x, -y, z))

    def test_head_first_with_pixels_that_are_not_square(self):
        self.check("HFS", 60, 77, 2.0, 1.0, lambda x, y, z: (x, -y, z))

    def test_feet_first(self):
        self.check("FFS", 32, 32, 2.0, 2.0, lambda x, y, z: (-x, -y, -z))
        self.check("FFS", 60, 77, 2.0, 1.0, lambda x, y, z: (-x, -y, -z))

    def test_pixel_spacing_is_row_spacing_first(self):
        self.assertEqual(plane((10, 20), 2.0, 1.0, 0.0, "HFS")["PixelSpacing"], [2.0, 1.0])

    def test_the_orientation_is_two_perpendicular_unit_vectors_columns_to_the_back(self):
        for position in ("HFS", "FFS"):
            iop = np.array(plane((8, 8), 2.0, 2.0, 0.0, position)["ImageOrientationPatient"])
            self.assertTrue(np.allclose(np.linalg.norm(iop[:3]), 1.0))
            self.assertTrue(np.allclose(np.linalg.norm(iop[3:]), 1.0))
            self.assertAlmostEqual(float(iop[:3] @ iop[3:]), 0.0)
            self.assertTrue(np.allclose(iop[3:], [0.0, 1.0, 0.0]))

    def test_an_unknown_position_is_refused(self):
        for position in ("HFP", "FFP", "", "hfs"):
            with self.subTest(position=position), self.assertRaises(ValueError):
                plane((8, 8), 2.0, 2.0, 0.0, position)


if __name__ == "__main__":
    unittest.main()
