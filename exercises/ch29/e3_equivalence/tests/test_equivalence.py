# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 29.3."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

from equivalence import assert_same
from projectors import Parallel

REF = Parallel()


class Accepts(unittest.TestCase):
    def test_the_same_projector(self):
        assert_same(REF, Parallel())

    def test_the_same_algorithm_in_single_precision(self):
        assert_same(REF, Parallel(dtype=np.float32), rtol=1e-5)


class Refuses(unittest.TestCase):
    def refuses(self, candidate, what, rtol=1e-6):
        with self.assertRaisesRegex(AssertionError, what):
            assert_same(REF, candidate, rtol=rtol)

    def test_angles_half_a_view_off(self):
        self.refuses(Parallel(phi_shift=np.pi / 72), "forward")

    def test_s_reversed(self):
        self.refuses(Parallel(s_sign=-1.0), "forward")

    def test_a_backprojector_that_is_not_the_adjoint(self):
        self.refuses(Parallel(nearest_back=True), "back")

    def test_a_scale_error_of_1e_4(self):
        self.refuses(Parallel(scale=1.0 + 1e-4), "forward", rtol=1e-5)

    def test_another_geometry(self):
        self.refuses(Parallel(bins=43), "geometry")


if __name__ == "__main__":
    unittest.main()
