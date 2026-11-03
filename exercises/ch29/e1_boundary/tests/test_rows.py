# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 29.1."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import rows


class Boundary(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.a = rng.random((6, 5))
        self.f = rng.uniform(0.5, 2.0, 6)
        self.want = self.a * self.f[:, None]

    def test_scales_each_row(self):
        self.assertTrue(np.allclose(rows.scale_rows(self.a, self.f), self.want, rtol=1e-15))

    def test_any_layout_gives_the_same_answer(self):
        fortran = np.asfortranarray(self.a)
        self.assertTrue(np.allclose(rows.scale_rows(fortran, self.f), self.want, rtol=1e-15))
        big = np.random.default_rng(2).random((12, 15))
        view = big[::2, ::3]                       # a strided view, not contiguous
        self.assertTrue(np.allclose(rows.scale_rows(view, self.f), view * self.f[:, None],
                                    rtol=1e-15))
        transposed = np.ascontiguousarray(self.a.T).T  # Fortran order by transposition
        self.assertTrue(np.allclose(rows.scale_rows(transposed, self.f), self.want, rtol=1e-15))

    def test_other_dtypes_are_converted(self):
        ints = np.arange(30, dtype=np.int32).reshape(6, 5)
        got = rows.scale_rows(ints, self.f)
        self.assertEqual(got.dtype, np.float64)
        self.assertTrue(np.allclose(got, ints * self.f[:, None], rtol=1e-15))

    def test_wrong_shapes_are_refused_with_a_reason(self):
        with self.assertRaisesRegex(ValueError, "2-dimensional, got shape \\(30,\\)"):
            rows.scale_rows(np.zeros(30), self.f)
        with self.assertRaisesRegex(ValueError, "one value per row of a, 6, got shape \\(5,\\)"):
            rows.scale_rows(self.a, np.ones(5))
        with self.assertRaisesRegex(ValueError, "got shape \\(6, 1\\)"):
            rows.scale_rows(self.a, np.ones((6, 1)))

    def test_the_input_is_left_alone(self):
        keep = self.a.copy()
        out = rows.scale_rows(self.a, self.f)
        self.assertTrue(np.array_equal(self.a, keep))
        self.assertFalse(np.shares_memory(out, self.a))


if __name__ == "__main__":
    unittest.main()
