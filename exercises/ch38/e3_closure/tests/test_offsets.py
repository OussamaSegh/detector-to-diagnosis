# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 38.3."""
import random
import unittest

from offsets import solve


def all_pairs(truth, variance=100.0, noise=None, rng=None):
    n = len(truth)
    out = []
    for a in range(n):
        for b in range(a + 1, n):
            s = truth[b] - truth[a]
            if noise:
                s += rng.gauss(0.0, noise)
            out.append((a, b, s, variance))
    return out


class Exact(unittest.TestCase):
    def test_exact_shifts_give_the_offsets_with_a_mean_of_zero(self):
        truth = [10.0, -20.0, 35.0, 0.0, 5.0]
        r = solve(5, all_pairs(truth))
        mean = sum(truth) / 5
        for got, want in zip(r.offset, truth):
            self.assertAlmostEqual(got, want - mean, places=6)
        self.assertEqual(r.groups, 1)
        self.assertAlmostEqual(r.chi2, 0.0, places=6)
        self.assertEqual(r.dof, 10 - 4)

    def test_a_chain_has_the_uncertainty_of_its_pairs(self):
        # Two blocks, one pair of variance 400: each offset is half the shift, sigma 10.
        r = solve(2, [(0, 1, 100.0, 400.0)])
        self.assertAlmostEqual(r.offset[0], -50.0, places=6)
        self.assertAlmostEqual(r.offset[1], 50.0, places=6)
        self.assertAlmostEqual(r.sigma[0], 10.0, places=6)
        self.assertEqual(r.dof, 0)


class Redundancy(unittest.TestCase):
    def test_every_pair_counts_and_the_weights_too(self):
        # Eight blocks, every pair measured with noise of 20, and one pair measured 100 times
        # worse but declared so. A spanning tree uses a handful of the 28 pairs; the fit, all.
        rng = random.Random(38)
        errs = []
        for trial in range(20):
            truth = [rng.uniform(-200, 200) for _ in range(8)]
            pairs = all_pairs(truth, variance=400.0, noise=20.0, rng=rng)
            a, b, s, _ = pairs[0]
            pairs[0] = (a, b, s + rng.gauss(0.0, 2000.0), 4_000_000.0)
            r = solve(8, pairs)
            mean = sum(truth) / 8
            errs += [(o - (t - mean)) ** 2 for o, t in zip(r.offset, truth)]
        rms = (sum(errs) / len(errs)) ** 0.5
        self.assertLess(rms, 10.0)  # about 20 / sqrt(8 / 2) = 10 at best

    def test_groups_are_solved_apart_and_a_lone_block_is_unobserved(self):
        pairs = [(0, 1, 30.0, 1.0), (2, 3, -10.0, 1.0), (3, 4, 40.0, 1.0)]
        r = solve(6, pairs)
        self.assertEqual(r.groups, 2)
        self.assertEqual(r.observed, [True, True, True, True, True, False])
        self.assertAlmostEqual(r.offset[0] + r.offset[1], 0.0, places=6)
        self.assertAlmostEqual(r.offset[2] + r.offset[3] + r.offset[4], 0.0, places=6)
        self.assertAlmostEqual(r.offset[4] - r.offset[3], 40.0, places=6)
        self.assertEqual(r.sigma[5], 0.0)


class Closure(unittest.TestCase):
    def test_shifts_that_no_block_clocks_explain_give_a_large_chi2(self):
        # Around the loop 0 -> 1 -> 2 -> 0 the shifts of block clocks sum to zero; a swapped pair
        # of cables adds 300 to one pair only, which no set of offsets can reproduce.
        truth = [0.0, 50.0, -30.0, 10.0]
        pairs = all_pairs(truth, variance=100.0)
        good = solve(4, pairs)
        a, b, s, v = pairs[0]
        pairs[0] = (a, b, s + 300.0, v)
        bad = solve(4, pairs)
        self.assertLess(good.chi2 / good.dof, 0.01)
        self.assertGreater(bad.chi2 / bad.dof, 50.0)


if __name__ == "__main__":
    unittest.main()
