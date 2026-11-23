#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the C++ projector through its Python module, recon_cpp (Chapter 29, tool TL-31).

The projection and reconstruction tests of tools/test_recon.py run again with the C++ projector
in place of the numpy one, so both sides of the boundary meet the same requirements; then the two
are compared line by line on MiniDAQ's geometry, and the binding is given what it must refuse.
CTest sets MINIDAQ_RECON_CPP to the module's build directory; without the module the test fails,
since the build that registers it also builds the module.

    MINIDAQ_RECON_CPP=build/debug/recon tools/test_recon_cpp.py
"""
import pickle
import sys
import unittest

try:
    import numpy as np
except ImportError:
    print("numpy is not installed: skipped")
    sys.exit(77)

import test_recon as base
from test_recon import header, mlem, project

project.load_cpp()  # fail now, with the ImportError, if the module is not there


def cpp(s, phi, n=128, pixel_mm=2.0):
    return project.CppProjector(s, phi, n=n, pixel_mm=pixel_mm, threads=4)


# [snippet:same-tests]
class CppProjection(base.Projection):
    make = staticmethod(cpp)


class CppReconstruction(base.Reconstruction):
    make = staticmethod(cpp)
# [/snippet:same-tests]


class CppImageQuality(base.ImageQuality):
    make = staticmethod(cpp)


def cpp_tof(s, phi, n=128, pixel_mm=2.0, **tof):
    return project.CppTofProjector(s, phi, n=n, pixel_mm=pixel_mm, threads=4, **tof)


class CppTofProjection(base.TofProjection):
    make = staticmethod(cpp_tof)


class CppTofReconstruction(base.TofReconstruction):
    make = staticmethod(cpp_tof)


class SameAsNumpy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s, phi = project.bin_lines(header(), radius_mm=156.0)
        cls.py = project.Projector(s, phi, n=128, pixel_mm=2.0)
        cls.cc = cpp(s, phi, n=128, pixel_mm=2.0)

    def test_the_projections_agree_line_by_line(self):
        # REQ: SRS-REC-004
        rng = np.random.default_rng(11)
        x = rng.random((128, 128))
        a, b = self.py.forward(x), self.cc.forward(x)
        # The numpy projector keeps its weights in float32: about 1e-7 relative.
        self.assertLess(np.abs(a - b).max() / np.abs(a).max(), 1e-6)
        y = rng.random(a.shape)
        a, b = self.py.back(y), self.cc.back(y)
        self.assertLess(np.abs(a - b).max() / np.abs(a).max(), 1e-6)

    def test_osem_gives_the_same_image(self):
        # REQ: SRS-REC-004
        xs, ys = self.py.pixel_centers()
        truth = ((xs ** 2 + ys ** 2) <= 80.0 ** 2) * 1.0 + ((xs - 30) ** 2 + ys ** 2 <= 100) * 3.0
        rng = np.random.default_rng(12)
        mult = rng.uniform(0.5, 1.0, self.py.shape)
        y = rng.poisson(mlem.expected(truth, self.py, mult, 0.3)).astype(float)
        a = mlem.osem(y, self.py, mult, 0.3, 3, n_subsets=8)
        b = mlem.osem(y, self.cc, mult, 0.3, 3, n_subsets=8)
        self.assertLess(np.abs(a - b).max() / a.max(), 1e-5)


class TofSameAsNumpy(unittest.TestCase):
    def test_the_tof_projections_agree_line_by_line(self):
        # REQ: SRS-REC-004, SRS-REC-007
        s, phi = project.bin_lines(header(), radius_mm=156.0)
        tof = {"tof_bins": 15, "tof_bin_ps": 120.0, "ctr_fwhm_ps": 350.0}
        py = project.TofProjector(s, phi, n=64, pixel_mm=3.0, **tof)
        cc = cpp_tof(s, phi, n=64, pixel_mm=3.0, **tof)
        self.assertEqual(py.shape, tuple(cc.shape))
        rng = np.random.default_rng(13)
        x = rng.random((64, 64))
        a, b = py.forward(x), cc.forward(x)
        # float32 weights and an erf within 1.5e-7 on the numpy side.
        self.assertLess(np.abs(a - b).max() / np.abs(a).max(), 1e-6)
        y = rng.random(a.shape)
        a, b = py.back(y), cc.back(y)
        self.assertLess(np.abs(a - b).max() / np.abs(a).max(), 1e-6)
        with self.assertRaises(ValueError):  # a sinogram without its TOF bins
            cc.back(y[..., 0])


class TheBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s, phi = project.bin_lines(header())
        cls.s, cls.phi = s, phi
        cls.A = cpp(s, phi, n=32, pixel_mm=8.0)

    def test_refuses_arrays_of_the_wrong_shape(self):
        # REQ: SRS-REC-005
        with self.assertRaisesRegex(ValueError, "image must be 32 x 32, got 32 x 31"):
            self.A.forward(np.zeros((32, 31)))
        with self.assertRaisesRegex(ValueError, "got 1024"):
            self.A.forward(np.zeros(1024))
        with self.assertRaisesRegex(ValueError, "sinogram must be 2 x"):
            self.A.back(np.zeros(self.s.shape), views=[0, 1])
        with self.assertRaises(ValueError):
            project.CppProjector(self.s, self.phi[:, :-1], n=32, pixel_mm=8.0)
        with self.assertRaises(ValueError):
            project.CppProjector(self.s, self.phi, n=32, pixel_mm=-1.0)

    def test_refuses_views_that_do_not_exist(self):
        # REQ: SRS-REC-005
        with self.assertRaises(IndexError):
            self.A.forward(np.zeros((32, 32)), views=[0, 192])
        with self.assertRaises(IndexError):
            self.A.forward(np.zeros((32, 32)), views=[-1])

    def test_converts_other_dtypes_and_layouts(self):
        # REQ: SRS-REC-005
        rng = np.random.default_rng(13)
        x = rng.random((32, 32))
        want = self.A.forward(x)
        self.assertTrue(np.array_equal(self.A.forward(np.asfortranarray(x)), want))
        self.assertTrue(np.array_equal(self.A.forward(x.T.copy().T), want))
        big = rng.random((64, 64))
        self.assertTrue(np.array_equal(self.A.forward(big[::2, ::2]),
                                       self.A.forward(big[::2, ::2].copy())))
        ints = (x * 10).astype(np.int32)
        self.assertTrue(np.array_equal(self.A.forward(ints), self.A.forward(ints.astype(float))))

    def test_leaves_its_inputs_alone_and_returns_new_arrays(self):
        # REQ: SRS-REC-005
        x = np.ones((32, 32))
        keep = x.copy()
        a = self.A.forward(x)
        b = self.A.forward(x)
        self.assertTrue(np.array_equal(x, keep))
        self.assertFalse(np.shares_memory(a, b))
        self.assertEqual(a.dtype, np.float64)
        self.assertEqual(a.shape, self.s.shape)

    def test_writes_into_an_output_the_caller_gives(self):
        # REQ: SRS-REC-009
        m = self.A._p  # the module's Projector, which takes out=
        rng = np.random.default_rng(14)
        x = rng.random((32, 32))
        sino = np.full(self.s.shape, np.nan)
        got = m.forward(x, out=sino)
        self.assertIs(got, sino)  # the caller's array, no copy
        self.assertTrue(np.array_equal(sino, m.forward(x)))
        image = np.empty((32, 32))
        self.assertIs(m.back(sino, out=image), image)
        self.assertTrue(np.array_equal(image, m.back(sino)))
        two = np.zeros((2, self.s.shape[1]))
        m.forward(x, views=[3, 7], out=two)
        self.assertTrue(np.array_equal(two, m.forward(x, views=[3, 7])))
        rows = np.zeros((64, 32))  # the C-contiguous rows of a larger array are written in place
        m.back(sino, out=rows[:32])
        self.assertTrue(np.array_equal(rows[:32], image))
        self.assertFalse(rows[32:].any())
        # float64 whatever its dtype object: an unpickled array has one of its own (MDQ-PR-088)
        unpickled = pickle.loads(pickle.dumps(np.zeros(self.s.shape)))
        self.assertIs(m.forward(x, out=unpickled), unpickled)
        self.assertTrue(np.array_equal(unpickled, sino))

    def test_refuses_an_output_it_cannot_write_in_place(self):
        # REQ: SRS-REC-009
        m = self.A._p
        x = np.ones((32, 32))
        for out, reason in ((np.zeros(self.s.shape, dtype=np.float32), "float64"),
                            (np.zeros(self.s.shape, order="F"), "C-contiguous"),
                            (np.zeros((self.s.shape[0], 2 * self.s.shape[1]))[:, ::2],
                             "C-contiguous"),
                            (np.zeros((self.s.shape[0], self.s.shape[1] + 1)), "got"),
                            (np.zeros(self.s.size), "got"),
                            (np.zeros(self.s.shape, dtype=">f8"), "float64")):
            keep = out.copy()
            with self.assertRaisesRegex(ValueError, reason):
                m.forward(x, out=out)
            self.assertTrue(np.array_equal(out, keep))
        ro = np.zeros(self.s.shape)
        ro.flags.writeable = False
        with self.assertRaisesRegex(ValueError, "read-only"):
            m.forward(x, out=ro)
        with self.assertRaises(TypeError):
            m.back(np.zeros(self.s.shape), out=[[0.0] * 32] * 32)
        sino = np.zeros(self.s.shape)
        inside = sino.reshape(-1)[:1024].reshape(32, 32)  # an image in the sinogram's memory
        with self.assertRaisesRegex(ValueError, "shares memory"):
            m.back(sino, out=inside)


if __name__ == "__main__":
    unittest.main()
