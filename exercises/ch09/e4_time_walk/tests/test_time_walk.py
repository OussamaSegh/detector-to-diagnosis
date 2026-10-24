# SPDX-License-Identifier: MIT
import math
import unittest

import time_walk as tw

# Amplitude 1.0 at 511 keV; a threshold of 0.02 is "about 10 keV".
THRESHOLD = 0.02


def amplitude(kev):
    return kev / 511.0


class TimeWalk(unittest.TestCase):
    def test_leading_edge_is_precise(self):
        t = tw.leading_edge_ns(THRESHOLD, 1.0)
        self.assertAlmostEqual(tw.pulse(t, 1.0), THRESHOLD, delta=1e-6)

    def test_a_small_pulse_crosses_later(self):
        energies = [100.0, 200.0, 350.0, 511.0, 650.0]
        walk = tw.walk_ps(lambda e: tw.leading_edge_ns(THRESHOLD, amplitude(e)), energies)
        self.assertTrue(all(a > b for a, b in zip(walk, walk[1:])), walk)
        self.assertGreater(walk[0], 20.0, "a 100 keV pulse crosses tens of ps later than 511 keV")
        self.assertEqual(walk[3], 0.0)

    def test_constant_fraction_has_no_walk(self):
        energies = [100.0, 200.0, 350.0, 511.0, 650.0]
        walk = tw.walk_ps(lambda e: tw.constant_fraction_ns(0.1, amplitude(e)), energies)
        for w in walk:
            self.assertLess(abs(w), 0.01)

    def test_below_threshold_never_crosses(self):
        self.assertIsNone(tw.leading_edge_ns(THRESHOLD, 0.01))
        self.assertEqual(tw.time_over_threshold_ns(THRESHOLD, 0.01), 0.0)

    def test_time_over_threshold_is_logarithmic(self):
        # On the exponential tail, doubling the amplitude adds tau_decay * ln 2.
        t1 = tw.time_over_threshold_ns(THRESHOLD, amplitude(300.0))
        t2 = tw.time_over_threshold_ns(THRESHOLD, amplitude(600.0))
        self.assertAlmostEqual(t2 - t1, tw.TAU_DECAY_NS * math.log(2.0), delta=0.02 * 27.7)
        self.assertGreater(t1, 100.0, "ToT of a LYSO pulse at a low threshold: over 100 ns")


if __name__ == "__main__":
    unittest.main()
