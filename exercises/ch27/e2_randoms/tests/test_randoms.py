# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 27.2, on a ring of crystals whose singles rates are known."""
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import randoms

N = 192
TAU_PS = 4_000
SECONDS = 60.0


def fan(width=48):
    """Crystal pairs that the sorter accepts: across the ring, within +-width of opposite."""
    i, j = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    sep = np.minimum(np.abs(i - j), N - np.abs(i - j))
    return (sep >= N // 2 - width) & (i != j)


def singles(rng):
    """Counts in SECONDS: 20 to 60 kHz, higher on one side (an off-center source)."""
    angle = np.arange(N) * 2 * np.pi / N
    rate = 40e3 * (1 + 0.5 * np.cos(angle)) * rng.uniform(0.9, 1.1, N)
    return rate * SECONDS


def delayeds(rng, mean):
    upper = np.triu(rng.poisson(np.triu(mean, 1)), 1)
    return (upper + upper.T).astype(float)


def fan_z(estimate, mean):
    """Each crystal's fan sum, estimate against truth, in standard deviations of a Poisson count."""
    want = mean.sum(axis=1)
    return np.abs(estimate.sum(axis=1) - want) / np.sqrt(want)


class FromSingles(unittest.TestCase):
    def test_two_tau_s_a_s_b(self):
        s = np.full(N, 1e6)  # 1e6 counts in 60 s
        r = randoms.from_singles(s, TAU_PS, SECONDS, fan())
        want = 2 * TAU_PS * 1e-12 * (1e6 / SECONDS) ** 2 * SECONDS
        self.assertAlmostEqual(r[0, N // 2], want, delta=1e-9 * want)
        self.assertEqual(r[0, 1], 0.0, "outside the fan")
        self.assertTrue(np.array_equal(r, r.T))

    def test_follows_the_rates(self):
        rng = np.random.default_rng(1)
        s = singles(rng)
        f = fan()
        r = randoms.from_singles(s, TAU_PS, SECONDS, f)
        rate = s / SECONDS
        want = np.where(f, 2 * TAU_PS * 1e-12 * np.outer(rate, rate) * SECONDS, 0.0)
        self.assertLess(np.abs(r - want).max(), 1e-9 * want.max())


class VarianceReduced(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(2)
        self.f = fan()
        s = singles(rng)
        self.mean = randoms.from_singles(s, TAU_PS, SECONDS, self.f)
        self.d = delayeds(rng, self.mean)

    def test_unbiased_for_every_crystal(self):
        r = randoms.variance_reduced(self.d, self.f)
        self.assertEqual(r[~self.f].max(), 0.0)
        self.assertAlmostEqual(r.sum() / self.mean.sum(), 1.0, delta=0.003)
        # Each crystal's fan: the estimate's against the truth's, in units of the Poisson noise
        # of the crystal's delayed fan sum (about 0.4% here), which no estimator can beat.
        self.assertLess(fan_z(r, self.mean).max(), 4.5)

    def test_much_less_noise_than_the_delayeds(self):
        r = randoms.variance_reduced(self.d, self.f)
        m = self.f
        noise_d = np.sqrt(((self.d - self.mean)[m] ** 2).mean())
        noise_r = np.sqrt(((r - self.mean)[m] ** 2).mean())
        self.assertLess(noise_r, 0.15 * noise_d)

    def test_a_narrow_fan(self):
        # With a fan of +-16 crystals each crystal meets a sixth of the ring: an estimate that
        # assumes every crystal meets every other is biased crystal by crystal.
        rng = np.random.default_rng(3)
        f = fan(16)
        s = singles(rng)
        mean = randoms.from_singles(s, TAU_PS, SECONDS, f)
        d = delayeds(rng, mean)
        r = randoms.variance_reduced(d, f)
        self.assertLess(fan_z(r, mean).max(), 4.5)
        self.assertAlmostEqual(r.sum() / mean.sum(), 1.0, delta=0.004)


if __name__ == "__main__":
    unittest.main()
