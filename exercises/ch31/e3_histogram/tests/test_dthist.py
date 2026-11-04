# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 31.3."""
import time
import unittest

import numpy as np
import dthist
from dthist import histogram

CRYSTALS, LO, BIN, BINS = 576, -2000, 20, 200


def python_loop(crystal, dt, crystals, lo, bin_ps, bins):
    """The slow reference: one Python iteration per entry."""
    counts = [[0] * bins for _ in range(crystals)]
    outside = 0
    for c, t in zip(crystal.tolist(), dt.tolist()):
        k = (t - lo) // bin_ps  # Python's // is floor division
        if 0 <= k < bins:
            counts[c][k] += 1
        else:
            outside += 1
    return np.array(counts, dtype=np.uint32), outside


def numpy_reference(crystal, dt, crystals, lo, bin_ps, bins):
    k = np.floor_divide(dt.astype(np.int64) - lo, bin_ps)
    inside = (k >= 0) & (k < bins)
    flat = np.bincount(crystal[inside].astype(np.int64) * bins + k[inside],
                       minlength=crystals * bins)
    return flat.reshape(crystals, bins).astype(np.uint32), int(np.count_nonzero(~inside))


class Histogram(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(313)
        self.crystal = rng.integers(0, CRYSTALS, 200_000).astype(np.int32)
        self.dt = np.rint(rng.normal(-40, 300, 200_000)).astype(np.int32)

    def test_agrees_with_the_reference_bin_for_bin(self):
        counts, outside = histogram(self.crystal, self.dt, CRYSTALS, LO, BIN, BINS)
        want, want_outside = numpy_reference(self.crystal, self.dt, CRYSTALS, LO, BIN, BINS)
        self.assertEqual(counts.dtype, np.uint32)
        self.assertEqual(counts.shape, (CRYSTALS, BINS))
        np.testing.assert_array_equal(counts, want)
        self.assertEqual(outside, want_outside)

    def test_the_edges(self):
        """lo is in the first bin; lo - 1 and lo + bins * bin are outside; negative times too."""
        crystal = np.zeros(5, dtype=np.int32)
        dt = np.array([LO, LO - 1, LO - BIN + 1, LO + BINS * BIN - 1, LO + BINS * BIN],
                      dtype=np.int32)
        counts, outside = histogram(crystal, dt, 1, LO, BIN, BINS)
        self.assertEqual(counts[0, 0], 1)
        self.assertEqual(counts[0, BINS - 1], 1)
        self.assertEqual(outside, 3)

    def test_converts_other_integer_types(self):
        counts, outside = histogram(self.crystal.astype(np.int64), self.dt.astype(np.int64),
                                    CRYSTALS, LO, BIN, BINS)
        want, want_outside = numpy_reference(self.crystal, self.dt, CRYSTALS, LO, BIN, BINS)
        np.testing.assert_array_equal(counts, want)

    def test_refuses_what_it_cannot_read(self):
        with self.assertRaises(ValueError):
            histogram(self.crystal, self.dt[:-1], CRYSTALS, LO, BIN, BINS)
        with self.assertRaises(ValueError):
            histogram(self.crystal, self.dt, 10, LO, BIN, BINS)  # crystal ids up to 575

    def test_is_much_faster_than_the_python_loop(self):
        # CAPA-0001: a speed test, in its margin table. Only an optimized module is timed: the
        # debug build ran 4.2 times the loop's speed in CI (MDQ-PR-047). Each side is the best of
        # five runs, because a single run can include a page fault or a preemption; a correct
        # solution reached 29 times the loop at the slowest, with four other processes busy.
        if not getattr(dthist, "optimized", False):
            self.skipTest("speed is only checked in an optimized build")
        n = 50_000
        crystal, dt = self.crystal[:n], self.dt[:n]

        def best(f):
            times = []
            for _ in range(5):
                t0 = time.perf_counter()
                out = f()
                times.append(time.perf_counter() - t0)
            return min(times), out

        t_loop, slow = best(lambda: python_loop(crystal, dt, CRYSTALS, LO, BIN, BINS))
        t_cpp, fast = best(lambda: histogram(crystal, dt, CRYSTALS, LO, BIN, BINS))
        np.testing.assert_array_equal(fast[0], slow[0])
        self.assertLess(t_cpp * 15, t_loop, f"C++ {t_cpp:.5f} s, loop {t_loop:.5f} s")

if __name__ == "__main__":
    unittest.main()
