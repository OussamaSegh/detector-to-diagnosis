# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 26.3, on the pairs of a small synthetic scanner."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import offsets as o

PER_RING, RINGS = 384, 4
N = PER_RING * RINGS


def pairs(rng, m, fan=60, ctr_sigma_ps=127.0, randoms=0.0, delay_sigma_ps=600.0):
    """m pairs of a ring scanner. Each pair joins a crystal with one in a fan of +-fan crystals
    across the ring and in any ring, as a centered cylinder gives (fan 0: only the crystal
    opposite, as a point source at the center gives). Returns (ci, cj, dt, the true delays, and
    which pairs are random)."""
    d = rng.normal(0.0, delay_sigma_ps, N)
    ring = rng.integers(0, RINGS, m)
    pos = rng.integers(0, PER_RING, m)
    ci = ring * PER_RING + pos
    other = (pos + PER_RING // 2 + rng.integers(-fan, fan + 1, m)) % PER_RING
    # A cylinder's lines cross the rings in every combination; a centered point's join a ring
    # only with its mirror image.
    ring_j = rng.integers(0, RINGS, m) if fan else RINGS - 1 - ring
    cj = ring_j * PER_RING + other
    dt = d[ci] - d[cj] + rng.normal(0.0, ctr_sigma_ps, m)
    random = rng.random(m) < randoms
    dt[random] = rng.uniform(-4_000.0, 4_000.0, random.sum())
    return ci, cj, dt, d, random


def error(found, truth):
    e = found - truth
    return e - e.mean()


class Graph(unittest.TestCase):
    def test_counts_the_parts(self):
        self.assertEqual(o.components(np.array([0, 1, 3]), np.array([1, 2, 4]), 6), 2)
        self.assertEqual(o.components(np.array([0, 2]), np.array([1, 3]), 4), 2)
        self.assertEqual(o.components(np.array([0, 1, 2]), np.array([1, 2, 3]), 4), 1)
        # A long chain: 0 - 1 - 2 - ... - 999.
        chain = np.arange(999)
        self.assertEqual(o.components(chain[::-1], chain[::-1] + 1, 1000), 1)

    def test_a_point_source_leaves_the_graph_in_pieces(self):
        rng = np.random.default_rng(1)
        ci, cj, dt, _, _ = pairs(rng, 200_000, fan=0)
        self.assertGreater(o.components(ci, cj, N), 100)
        with self.assertRaises(ValueError):
            o.solve(ci, cj, dt, N)


class Delays(unittest.TestCase):
    def test_finds_the_delays_of_a_cylinder(self):
        rng = np.random.default_rng(2)
        ci, cj, dt, d, _ = pairs(rng, 120_000)  # about 160 pairs per crystal
        found = o.solve(ci, cj, dt, N)
        self.assertLess(abs(found.mean()), 1e-6)
        self.assertLess(error(found, d).std(), 15.0)  # 127 ps / sqrt(160) = 10 ps

    def test_exact_differences_give_exact_delays(self):
        rng = np.random.default_rng(3)
        ci, cj, _, d, _ = pairs(rng, 60_000, ctr_sigma_ps=0.0)
        self.assertLess(np.abs(error(o.solve(ci, cj, d[ci] - d[cj], N), d)).max(), 0.01)

    def test_sets_random_coincidences_aside(self):
        rng = np.random.default_rng(4)
        ci, cj, dt, d, random = pairs(rng, 120_000, randoms=0.15)
        found, kept = o.trimmed(ci, cj, dt, N)
        self.assertLess(error(found, d).std(), 15.0)
        self.assertGreater((~kept & random).sum(), 0.8 * random.sum())
        self.assertGreater(kept[~random].mean(), 0.99)


if __name__ == "__main__":
    unittest.main()
