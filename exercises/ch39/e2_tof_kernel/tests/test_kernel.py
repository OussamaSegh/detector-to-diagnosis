# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 39.2."""
import random
import unittest

from kernel import C_MM_PER_PS, bin_edges_mm, probabilities, sigma_mm


class Kernel(unittest.TestCase):
    def test_the_resolution_in_millimeters(self):
        self.assertAlmostEqual(sigma_mm(300.0), 19.0965, delta=1e-3)
        self.assertAlmostEqual(sigma_mm(600.0) / sigma_mm(300.0), 2.0, places=12)

    def test_the_edges_are_those_of_the_histogrammer(self):
        e = bin_edges_mm(5, 100.0)
        self.assertEqual(len(e), 6)
        self.assertAlmostEqual(e[0], -2.5 * 100.0 * C_MM_PER_PS / 2.0, places=9)
        self.assertAlmostEqual(e[3], 0.5 * 100.0 * C_MM_PER_PS / 2.0, places=9)

    def test_the_probabilities_add_up_to_one(self):
        for width, ctr in ((100.0, 300.0), (300.0, 100.0), (50.0, 250.0)):
            edges = bin_edges_mm(41, width)
            for x in (-20.0, 0.0, 3.7, 25.0):
                p = probabilities(x, edges, ctr)
                self.assertAlmostEqual(sum(p), 1.0, delta=1e-12, msg=(width, ctr, x))

    def test_a_point_at_the_middle_is_symmetric(self):
        p = probabilities(0.0, bin_edges_mm(13, 100.0), 300.0)
        for k in range(13):
            self.assertAlmostEqual(p[k], p[12 - k], places=14)

    def test_bins_wider_than_the_kernel(self):
        p = probabilities(0.0, bin_edges_mm(5, 300.0), 100.0)
        self.assertAlmostEqual(p[2], 0.99959, delta=1e-5)

    def test_simulated_timing_errors_fall_as_the_probabilities_say(self):
        rng = random.Random(39)
        edges = bin_edges_mm(9, 100.0)
        x, ctr, n = 12.0, 300.0, 200_000
        sigma_t = ctr / 2.3548200450309493
        counts = [0] * 9
        for _ in range(n):
            tau = 2.0 * x / C_MM_PER_PS + rng.gauss(0.0, sigma_t)   # the measured tau
            pos = C_MM_PER_PS * tau / 2.0
            for k in range(9):
                if edges[k] <= pos < edges[k + 1]:
                    counts[k] += 1
                    break
        p = probabilities(x, edges, ctr)
        chi2 = sum((c - n * q) ** 2 / (n * q) for c, q in zip(counts, p) if n * q > 5)
        self.assertLess(chi2 / 9, 2.0)


if __name__ == "__main__":
    unittest.main()
