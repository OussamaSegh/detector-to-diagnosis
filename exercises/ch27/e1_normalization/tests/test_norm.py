# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 27.1, on a small scanner whose crystal efficiencies are known."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import norm

RINGS, PER_RING = 4, 96
N = RINGS * PER_RING
ANGLE = (np.arange(PER_RING) + 0.5) * 2 * np.pi / PER_RING
RADIUS = 150.0


def expected(source_x=0.0, source_r=60.0):
    """What a perfect scanner records from a cylinder of activity (radius source_r, centered at
    x = source_x) per line between two crystals: the line's chord through the source, for every
    pair of crystals at least a quarter of the ring apart, in any two rings."""
    x, y = RADIUS * np.cos(ANGLE), RADIUS * np.sin(ANGLE)
    i, j = np.meshgrid(np.arange(PER_RING), np.arange(PER_RING), indexing="ij")
    dx, dy = x[j] - x[i], y[j] - y[i]
    length = np.hypot(dx, dy)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = np.abs((x[i] - source_x) * dy - y[i] * dx) / length
    chord = 2 * np.sqrt(np.clip(source_r ** 2 - dist ** 2, 0, None))
    sep = np.minimum(np.abs(i - j), PER_RING - np.abs(i - j))
    chord = np.where(sep >= PER_RING // 4, chord, 0.0)
    return np.tile(chord, (RINGS, RINGS))  # crystal = ring * PER_RING + position


def scan(rng, eff, e, counts_per_crystal):
    """Poisson counts of a scan with true efficiencies eff and perfect-scanner counts e."""
    mean = e * np.outer(eff, eff)
    mean *= counts_per_crystal * N / mean.sum()
    upper = np.triu(rng.poisson(np.triu(mean, 1)), 1)
    return upper + upper.T, mean


def efficiencies(rng):
    e = np.clip(rng.normal(0.9, 0.05, N), 0.5, 1.0)
    return e


class Efficiencies(unittest.TestCase):
    def check(self, counts, e, eff, per_crystal):
        found = norm.efficiencies(counts, e)
        self.assertEqual(found.shape, (N,))
        self.assertAlmostEqual(found.mean(), 1.0, places=9)
        err = found / (eff / eff.mean()) - 1
        poisson = 1 / np.sqrt(per_crystal)
        self.assertLess(err.std(), 1.3 * poisson)
        self.assertLess(abs(err).max(), 6 * poisson)
        return err

    def test_a_centered_cylinder(self):
        rng = np.random.default_rng(1)
        eff = efficiencies(rng)
        e = expected()
        counts, _ = scan(rng, eff, e, 40_000)
        self.check(counts, e, eff, 40_000)

    def test_a_cylinder_off_center(self):
        # Each crystal now sees the source from its own side: the fan sums differ even for
        # crystals of the same efficiency.
        rng = np.random.default_rng(2)
        eff = efficiencies(rng)
        e = expected(source_x=40.0)
        counts, _ = scan(rng, eff, e, 40_000)
        self.check(counts, e, eff, 40_000)


class Normalize(unittest.TestCase):
    def test_a_scan_normalized_is_what_a_perfect_scanner_records(self):
        rng = np.random.default_rng(3)
        eff = efficiencies(rng)
        e = expected()
        norm_counts, _ = scan(rng, eff, e, 40_000)
        found = norm.efficiencies(norm_counts, e)
        # A second scan, of another source, through the same crystals.
        e2 = expected(source_x=-30.0, source_r=40.0)
        counts, mean = scan(rng, eff, e2, 20_000)
        n, dead = norm.normalize(counts, found)
        self.assertEqual(dead.tolist(), [])
        # Unbiased: summed over lines, the normalized counts are the perfect scanner's, up to
        # one scale (the efficiencies' mean, which normalization leaves to the calibration).
        perfect = mean / np.outer(eff, eff)
        scale = n.sum() / perfect.sum()
        lines = perfect > 0.5 * perfect.max()
        ratio = n[lines].sum() / (scale * perfect[lines].sum())
        self.assertAlmostEqual(ratio, 1.0, delta=0.002)
        # And no pattern of the crystals is left: the rows (fans) agree with the perfect ones.
        fan = n.sum(axis=1) / (scale * perfect.sum(axis=1))
        self.assertLess(fan.std(), 2.5 / np.sqrt(counts.sum(axis=1).mean()))

    def test_a_dead_crystal(self):
        rng = np.random.default_rng(4)
        eff = efficiencies(rng)
        eff[17] = 0.0
        e = expected()
        counts, _ = scan(rng, eff, e, 20_000)
        found = norm.efficiencies(counts, e)
        self.assertEqual(found[17], 0.0)
        n, dead = norm.normalize(counts, found)
        self.assertEqual(dead.tolist(), [17])
        self.assertTrue(np.isfinite(n).all())
        self.assertEqual(n[17].max(), 0.0)
        self.assertEqual(n[:, 17].max(), 0.0)


if __name__ == "__main__":
    unittest.main()
