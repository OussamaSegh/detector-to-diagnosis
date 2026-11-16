# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 38.1."""
import random
import unittest

from ptp import estimate, offset_and_delay


def exchange(offset, forward, backward, t1=1000.0, turnaround=50.0):
    """Time stamps of one exchange with the given path delays in each direction (ns)."""
    t2 = t1 + forward + offset          # slave time
    t3 = t2 + turnaround                # slave time
    t4 = t3 - offset + backward         # master time
    return t1, t2, t3, t4


class OneExchange(unittest.TestCase):
    def test_a_symmetric_path_gives_the_offset_and_the_delay(self):
        for offset in (0.0, 250.0, -1234.5):
            o, d = offset_and_delay(*exchange(offset, 800.0, 800.0))
            self.assertAlmostEqual(o, offset, places=6)
            self.assertAlmostEqual(d, 800.0, places=6)

    def test_an_asymmetric_path_errs_by_half_the_asymmetry(self):
        o, d = offset_and_delay(*exchange(100.0, 900.0, 700.0))
        self.assertAlmostEqual(o, 100.0 + (900.0 - 700.0) / 2, places=6)
        self.assertAlmostEqual(d, 800.0, places=6)

    def test_the_turnaround_time_of_the_slave_does_not_matter(self):
        a = offset_and_delay(*exchange(42.0, 500.0, 500.0, turnaround=1.0))
        b = offset_and_delay(*exchange(42.0, 500.0, 500.0, turnaround=1e6))
        self.assertAlmostEqual(a[0], b[0], places=6)
        self.assertAlmostEqual(a[1], b[1], places=6)


class ManyExchanges(unittest.TestCase):
    def test_queueing_is_filtered_out(self):
        # A path of 800 ns each way; switches add 0 to 20 us of queueing to either direction, and
        # one exchange in ten meets none. The truth is 300 ns.
        rng = random.Random(38)
        exchanges = []
        for i in range(1000):
            q = (lambda: 0.0) if i % 10 == 0 else (lambda: rng.expovariate(1 / 5000.0))
            exchanges.append(exchange(300.0, 800.0 + q(), 800.0 + q(), t1=1000.0 * i))
        self.assertAlmostEqual(estimate(exchanges), 300.0, delta=5.0)

    def test_without_queueing_every_exchange_agrees(self):
        exchanges = [exchange(-75.0, 640.0, 640.0, t1=100.0 * i) for i in range(20)]
        self.assertAlmostEqual(estimate(exchanges), -75.0, places=6)


if __name__ == "__main__":
    unittest.main()
