# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 31.1."""
import pathlib
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mdql  # noqa: E402
from pairs import pair_counts  # noqa: E402

N = 18432


class PairCounts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "f.mdql"

    def tearDown(self):
        self.dir.cleanup()

    def write(self, r, block_records=1000):
        self.path.write_bytes(mdql.file_bytes(r, block_records))

    def test_a_pair_is_one_key_whichever_crystal_was_first(self):
        # Pair (10, 20) three times with 10 first and twice with 20 first; pair (5, 7) once.
        t = np.arange(6) * 1000
        a = [10, 10, 20, 10, 20, 7]
        b = [20, 20, 10, 20, 10, 5]
        self.write(mdql.records(t, a, b, [100] * 6, [511.0] * 6, [511.0] * 6))
        keys, counts = pair_counts(self.path)
        self.assertEqual(keys.tolist(), [5 * N + 7, 10 * N + 20])
        self.assertEqual(counts.tolist(), [1, 5])

    def test_delayeds_and_tags_are_not_counted(self):
        t = np.arange(4) * 1000
        r = mdql.records(t, [1, 1, 1, 1], [2, 2, 2, 2], [100, 100, 100_100, 100_100],
                         [511.0] * 4, [511.0] * 4, delayed=[False, False, True, True])
        self.write(mdql.concat(r, mdql.tag(500), mdql.tag(1500, kind=1, value=7)))
        keys, counts = pair_counts(self.path)
        self.assertEqual(keys.tolist(), [1 * N + 2])
        self.assertEqual(counts.tolist(), [2])

    def test_agrees_with_a_direct_count_over_many_blocks(self):
        rng = np.random.default_rng(311)
        n = 50_000
        a = rng.integers(0, 300, n)
        b = (a + 1 + rng.integers(0, 299, n)) % 300
        delayed = rng.random(n) < 0.05
        r = mdql.records(np.arange(n) * 10, a, b, np.full(n, 50), np.full(n, 511.0),
                         np.full(n, 511.0), delayed)
        self.write(r, block_records=777)
        keys, counts = pair_counts(self.path)
        lo, hi = np.minimum(a, b)[~delayed], np.maximum(a, b)[~delayed]
        want_k, want_c = np.unique(lo * N + hi, return_counts=True)
        np.testing.assert_array_equal(keys, want_k)
        np.testing.assert_array_equal(counts, want_c)
        self.assertEqual(int(counts.sum()), int(np.count_nonzero(~delayed)))


if __name__ == "__main__":
    unittest.main()
