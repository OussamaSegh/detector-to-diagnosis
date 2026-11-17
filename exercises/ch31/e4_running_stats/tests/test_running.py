# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 31.4, on synthetic per-crystal values read in chunks."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import running as r

CRYSTALS = 64


def data(seed=31, n=200_000, offset=0.0):
    rng = np.random.default_rng(seed)
    crystal = rng.integers(0, CRYSTALS, n)
    centers = rng.normal(0.0, 300.0, CRYSTALS)
    values = offset + centers[crystal] + rng.normal(0.0, 50.0, n)
    return crystal, values


def reference(crystal, values):
    """Two passes over everything in memory: what the chunked pass must give. The values are first
    shifted by one of them, which is exact for values this close together."""
    base = values[0]
    x = values - base
    mean = np.array([x[crystal == c].mean() for c in range(CRYSTALS)]) + base
    var = np.array([x[crystal == c].var(ddof=1) for c in range(CRYSTALS)])
    return mean, var


def by_chunks(crystal, values, sizes):
    s = r.RunningStats(CRYSTALS)
    start = 0
    for size in sizes:
        s.add(crystal[start:start + size], values[start:start + size])
        start += size
    s.add(crystal[start:], values[start:])
    return s


class RunningStatsTest(unittest.TestCase):
    def test_equal_chunks_give_the_whole_run(self):
        crystal, values = data()
        s = by_chunks(crystal, values, [20_000] * 9)
        mean, var = reference(crystal, values)
        self.assertTrue(np.array_equal(s.n, np.bincount(crystal, minlength=CRYSTALS)))
        self.assertTrue(np.allclose(s.mean, mean, rtol=0, atol=1e-9))
        self.assertTrue(np.allclose(s.variance(), var, rtol=1e-9))

    def test_unequal_chunks_and_missing_crystals(self):
        crystal, values = data(seed=32)
        crystal[:1000] = 0  # a first chunk of crystal 0 only
        s = by_chunks(crystal, values, [1000, 7, 0, 150_000, 3])
        mean, var = reference(crystal, values)
        self.assertTrue(np.allclose(s.mean, mean, rtol=0, atol=1e-9))
        self.assertTrue(np.allclose(s.variance(), var, rtol=1e-9))

    def test_a_large_offset_costs_no_digits(self):
        # Time stamps in ps, an hour into a run: 3.6e15 ps, spread 50 ps.
        crystal, values = data(seed=33, offset=3.6e15)
        s = by_chunks(crystal, values, [50_000] * 3)
        _, var = reference(crystal, values)
        self.assertTrue(np.allclose(s.variance(), var, rtol=1e-6))

    def test_too_few_values_have_no_variance(self):
        s = r.RunningStats(3)
        s.add([0, 0, 1], [1.0, 3.0, 5.0])
        v = s.variance()
        self.assertEqual(v[0], 2.0)
        self.assertTrue(np.isnan(v[1]))
        self.assertTrue(np.isnan(v[2]))
        self.assertEqual(s.mean[1], 5.0)

    def test_a_crystal_outside_is_refused(self):
        s = r.RunningStats(3)
        with self.assertRaises(IndexError):
            s.add([0, 3], [1.0, 2.0])
        with self.assertRaises(ValueError):
            s.add([0, 1], [1.0])


if __name__ == "__main__":
    unittest.main()
