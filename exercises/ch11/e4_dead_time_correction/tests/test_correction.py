# SPDX-License-Identifier: MIT
import math
import unittest

import correction as c

NP, P = c.NON_PARALYZABLE, c.PARALYZABLE
TAU = 1e-6  # 1 us, the chapter's block dead time


class Correction(unittest.TestCase):
    def test_round_trip_on_the_low_branch(self):
        for model in (NP, P):
            for n in (1e3, 1e5, 3e5, 9e5):
                m = c.recorded_rate(model, n, TAU)
                self.assertAlmostEqual(c.true_rate(model, m, TAU) / n, 1.0, places=9, msg=f"{model} {n}")

    def test_non_paralyzable_by_hand(self):
        # n tau = 1: half is lost, m = 500,000/s.
        self.assertAlmostEqual(c.recorded_rate(NP, 1e6, TAU), 5e5)
        self.assertAlmostEqual(c.true_rate(NP, 5e5, TAU), 1e6, delta=1e-3)
        self.assertTrue(math.isnan(c.true_rate(NP, 1e6, TAU)), "a unit never records 1 / tau")

    def test_paralyzable_has_two_branches(self):
        m = c.recorded_rate(P, 3e5, TAU)  # also recorded at a higher true rate
        high = c.true_rate(P, m, TAU, branch="high")
        self.assertGreater(high, 1.0 / TAU)
        self.assertAlmostEqual(c.recorded_rate(P, high, TAU) / m, 1.0, places=9)
        self.assertAlmostEqual(high / 2.3646e6, 1.0, places=4)  # x exp(-x) = 0.3 exp(-0.3) at x = 2.3646
        # The maximum: m = 1 / (e tau) at n = 1 / tau, and nothing records more.
        top = 1.0 / (math.e * TAU)
        self.assertAlmostEqual(c.true_rate(P, top, TAU) * TAU, 1.0, places=5)
        self.assertTrue(math.isnan(c.true_rate(P, 1.01 * top, TAU)))

    def test_error_amplification(self):
        self.assertAlmostEqual(c.error_amplification(NP, 5e5, TAU), 1.5)
        self.assertAlmostEqual(c.error_amplification(P, 5e5, TAU), 2.0)
        # A numerical derivative agrees: (dn / n) / (dm / m).
        for model in (NP, P):
            n, h = 4e5, 1.0
            dm = c.recorded_rate(model, n + h, TAU) - c.recorded_rate(model, n - h, TAU)
            numeric = (2 * h / n) / (dm / c.recorded_rate(model, n, TAU))
            self.assertAlmostEqual(c.error_amplification(model, n, TAU) / numeric, 1.0, places=5)

    def test_correcting_a_simulated_unit(self):
        # 1 s at 500,000/s (n tau = 0.5): a third of the events (non-paralyzable)
        # or 39% (paralyzable) are lost, and the corrected rate is within 1%,
        # about four standard deviations. (Not at n tau = 1: there the
        # paralyzable correction amplifies every error without bound.)
        n = 5e5
        for model in (NP, P):
            m = c.simulate_recorded(model, n, TAU, 1.0, seed=4)
            self.assertLess(m, 0.7 * n, model)
            self.assertLess(abs(c.true_rate(model, m, TAU) / n - 1.0), 0.01, model)


if __name__ == "__main__":
    unittest.main()
