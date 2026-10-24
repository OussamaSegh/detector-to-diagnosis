# SPDX-License-Identifier: MIT
import unittest

import link_budget as lb

GBE = 1e9
TEN_GBE = 10e9


class LinkBudget(unittest.TestCase):
    def test_a_full_standard_frame(self):
        # 182 words: 1472 bytes of UDP payload, a 1518-byte frame, 1538 bytes of wire time.
        self.assertEqual(lb.packet_payload(182), 1472)
        self.assertEqual(lb.wire_bytes(1472), 1538)

    def test_a_tiny_frame_is_padded(self):
        self.assertEqual(lb.wire_bytes(1), 84)  # 64-byte minimum frame + 20

    def test_singles_per_link(self):
        self.assertAlmostEqual(lb.wire_bytes_per_single(182), 8.451, delta=0.001)
        self.assertAlmostEqual(lb.max_singles_per_s(GBE, 182) / 1e6, 14.79, delta=0.01)
        self.assertAlmostEqual(lb.max_singles_per_s(TEN_GBE, 182) / 1e6, 147.9, delta=0.1)

    def test_small_packets_cost_more(self):
        self.assertAlmostEqual(lb.wire_bytes_per_single(32), 10.5625, delta=1e-4)
        self.assertAlmostEqual(lb.max_singles_per_s(GBE, 32) / 1e6, 11.83, delta=0.01)
        self.assertGreater(lb.wire_bytes_per_single(1), 10 * lb.wire_bytes_per_single(182))

    def test_ten_million_singles(self):
        self.assertAlmostEqual(lb.utilization(10e6, 182, GBE), 0.676, delta=0.001)
        self.assertAlmostEqual(lb.packets_per_s(10e6, 182), 54945, delta=1)


if __name__ == "__main__":
    unittest.main()
