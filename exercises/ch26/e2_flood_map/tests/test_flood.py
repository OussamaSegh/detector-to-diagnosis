# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 26.2, on a synthetic flood whose crystals are known."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import flood as f

PIXELS = 256


def block(rng, events_per_crystal=400, blur_px=1.0, compress=0.25, bend=0.01):
    """Events of a flood of a 16 x 16 block: each crystal's true position on a regular grid, then
    the light sharing's distortion (edges compressed by `compress`, rows bent by `bend`), then a
    blur of `blur_px` pixels. Returns (u, v, true crystal, the centers in pixels [row][column])."""
    side = f.SIDE
    q = (np.arange(side) + 0.5) / side - 0.5  # -0.47 .. 0.47
    qr, qc = np.meshgrid(q, q, indexing="ij")

    def distort(a):
        return a * (1 - compress * (2 * a) ** 2)

    row = 0.5 + distort(qr) + bend * (2 * qc) ** 2  # the rows sag towards the block's sides
    col = 0.5 + distort(qc)
    centers = np.stack([row * PIXELS, col * PIXELS], -1)
    crystal = np.repeat(np.arange(side * side), events_per_crystal)
    blur = blur_px / PIXELS
    v = row.reshape(-1)[crystal] + rng.normal(0, blur, crystal.size)
    u = col.reshape(-1)[crystal] + rng.normal(0, blur, crystal.size)
    return u, v, crystal, centers


class Peaks(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(26)
        self.u, self.v, self.crystal, self.centers = block(self.rng)
        self.img = f.flood(self.u, self.v)

    def test_one_peak_per_crystal(self):
        peaks = f.find_peaks(self.img)
        self.assertEqual(peaks.shape, (256, 2))
        d = np.sqrt(((peaks[:, None, :] - self.centers.reshape(1, -1, 2)) ** 2).sum(-1))
        nearest = d.argmin(1)
        self.assertEqual(len(set(nearest.tolist())), 256, "two peaks on one crystal")
        self.assertLess(d.min(1).max(), 1.5, "a peak away from its crystal")

    def test_the_grid_is_in_the_order_of_the_crystals(self):
        grid = f.arrange(f.find_peaks(self.img))
        err = np.sqrt(((grid - self.centers) ** 2).sum(-1))
        self.assertLess(err.max(), 1.5)

    def test_the_lookup_table_identifies_the_crystals(self):
        table = f.lut(f.arrange(f.find_peaks(self.img)))
        found = f.identify(self.u, self.v, table)
        self.assertGreater((found == self.crystal).mean(), 0.98)


class HarderBlock(unittest.TestCase):
    def test_a_more_compressed_block_with_fewer_events(self):
        rng = np.random.default_rng(7)
        u, v, crystal, centers = block(rng, events_per_crystal=150, compress=0.3, bend=0.012)
        grid = f.arrange(f.find_peaks(f.flood(u, v)))
        err = np.sqrt(((grid - centers) ** 2).sum(-1))
        self.assertLess(np.median(err), 0.7)
        self.assertLess(err.max(), 2.0)
        found = f.identify(u, v, f.lut(grid))
        self.assertGreater((found == crystal).mean(), 0.95)

    def test_a_wrong_number_of_peaks_is_refused(self):
        with self.assertRaises(ValueError):
            f.arrange(np.zeros((255, 2)))


if __name__ == "__main__":
    unittest.main()
