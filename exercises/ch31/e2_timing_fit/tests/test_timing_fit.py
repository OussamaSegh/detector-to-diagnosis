# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 31.2."""
import math
import unittest

import numpy as np
from timing_fit import expected, fit_timing

EDGES = np.arange(-1500.0, 1520.0, 20.0)  # 151 bins of 20 ps
K = 2.0 * math.sqrt(2.0 * math.log(2.0))


def histogram(rng, area, background_per_ps, fwhm=300.0, mean=-40.0):
    mu = expected(EDGES, np.array([area, mean, fwhm / K, background_per_ps]))
    return rng.poisson(mu).astype(float)


class TimingFit(unittest.TestCase):
    def test_finds_a_strong_peak(self):
        rng = np.random.default_rng(1)
        r = fit_timing(histogram(rng, 100_000, 2.0), EDGES)
        for name, true in (("fwhm", 300.0), ("mean", -40.0), ("area", 100_000.0)):
            value, error = r[name]
            self.assertLess(abs(value - true), 4 * error, name)

    def test_a_weak_peak_is_not_biased(self):
        """300 coincidences in the peak on a background of 0.01 per ps: about 6 counts in the top
        bin and fewer than one in most. The mean area of 300 fits is within 3% of the truth."""
        rng = np.random.default_rng(2)
        areas = [fit_timing(histogram(rng, 300, 0.01), EDGES)["area"][0] for _ in range(300)]
        self.assertLess(abs(np.mean(areas) / 300.0 - 1.0), 0.03, np.mean(areas))

    def test_the_errors_are_the_spread(self):
        """Over 300 histograms, (FWHM - truth) / error has a standard deviation within 15% of 1."""
        rng = np.random.default_rng(3)
        pulls = []
        for _ in range(300):
            v, e = fit_timing(histogram(rng, 3_000, 0.2), EDGES)["fwhm"]
            pulls.append((v - 300.0) / e)
        self.assertLess(abs(np.std(pulls, ddof=1) - 1.0), 0.15, np.std(pulls, ddof=1))
        self.assertLess(abs(np.mean(pulls)), 0.2, np.mean(pulls))

    def test_refuses_too_few_counts(self):
        with self.assertRaises(ValueError):
            fit_timing(np.zeros(EDGES.size - 1), EDGES)


if __name__ == "__main__":
    unittest.main()
