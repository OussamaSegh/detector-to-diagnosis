# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 26.1, on synthetic spectra whose photopeak is known."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import photopeak as p

WIDTH = 4  # codes per bin, as tools/calib uses
BINS = 2048 // WIDTH


def spectrum(rng, peak_code, peak_counts, sigma_fraction=0.05, scatter=0.0, compton=1.0):
    """A histogram of codes: a Gaussian photopeak, a flat Compton continuum up to the Compton
    edge (a third of the peak's energy below it), and, with `scatter`, photons that scattered in
    the patient: a ramp from a third of the peak to 0.9 of it, blurred, `scatter` times the
    peak's counts."""
    codes = [rng.normal(peak_code, sigma_fraction * peak_code, peak_counts)]
    edge = peak_code * 340.7 / 511.0
    codes.append(rng.uniform(0.2 * peak_code, edge, int(compton * peak_counts)))
    n = int(scatter * peak_counts)
    if n:
        # Density rising linearly from a third of the peak's code to 0.9 of it (sqrt of a
        # uniform), then blurred by the detector's resolution like everything it measures.
        lo, hi = 0.33 * peak_code, 0.9 * peak_code
        e = lo + (hi - lo) * np.sqrt(rng.uniform(0, 1, n))
        codes.append(e + rng.normal(0, 1, n) * sigma_fraction * np.sqrt(e * peak_code))
    c = np.clip(np.round(np.concatenate(codes)), 0, 2047).astype(int)
    return np.bincount(c // WIDTH, minlength=BINS)


def found_code(h, lo_code=600, hi_code=2000):
    centre, sigma, ok = p.fit(h, lo_code // WIDTH, hi_code // WIDTH)
    return p.to_code(centre, WIDTH), sigma * WIDTH, ok


class Positions(unittest.TestCase):
    def test_a_bin_is_centred_between_its_first_and_last_code(self):
        self.assertEqual(p.to_code(0, 4), 1.5)
        self.assertEqual(p.to_code(255, 4), 1021.5)
        self.assertEqual(p.to_code(10.25, 1), 10.25)

    def test_gain_of_a_linear_detector(self):
        self.assertAlmostEqual(p.gain(1022.0), 1.0)
        self.assertAlmostEqual(p.gain(1124.2), 1.1)


class CleanPeak(unittest.TestCase):
    def test_centre_and_sigma_without_background(self):
        rng = np.random.default_rng(1)
        h = spectrum(rng, 1022.0, 50_000, compton=0.0)
        code, sigma, ok = found_code(h)
        self.assertTrue(ok)
        self.assertLess(abs(code / 1022.0 - 1), 0.001)
        self.assertLess(abs(sigma / (0.05 * 1022.0) - 1), 0.03)
        self.assertLess(abs(p.resolution(code, sigma) - 11.77), 0.4)


class OnABackground(unittest.TestCase):
    def test_patient_scatter_does_not_pull_the_peak_down(self):
        rng = np.random.default_rng(2)
        errors, widths = [], []
        for k in range(40):
            true = rng.uniform(800, 1300)
            h = spectrum(rng, true, 3_000, scatter=0.8)
            code, sigma, ok = found_code(h)
            self.assertTrue(ok, k)
            errors.append(code / true - 1)
            widths.append(sigma / (0.05 * true) - 1)
        errors, widths = np.array(errors), np.array(widths)
        self.assertLess(abs(errors.mean()), 0.002, "biased")
        self.assertLess(np.abs(errors).max(), 0.008)
        self.assertLess(abs(widths.mean()), 0.06, "sigma biased")

    def test_gains_of_many_crystals(self):
        rng = np.random.default_rng(3)
        true = rng.uniform(0.7, 1.3, 30)
        found = [p.gain(found_code(spectrum(rng, g * 1022.0, 2_000, scatter=0.3))[0])
                 for g in true]
        self.assertLess(np.std(np.array(found) / true - 1), 0.003)


if __name__ == "__main__":
    unittest.main()
