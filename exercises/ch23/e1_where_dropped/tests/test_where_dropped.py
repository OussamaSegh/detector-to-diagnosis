# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 23.1. Run with the starter or solution directory on PYTHONPATH
(CTest does this)."""
import unittest

from where_dropped import parse_snmp_udp, parse_softnet, report, socket_drops

SNMP = """Ip: Forwarding DefaultTTL
Ip: 2 64
Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors IgnoredMulti MemErrors
Udp: {in_dg} 0 {rcvbuf} 74511 {rcvbuf} 0 0 0 0
UdpLite: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors IgnoredMulti MemErrors
UdpLite: 0 0 0 0 0 0 0 0 0
"""

SOFTNET = """{p0:08x} {d0:08x} 00000002 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
0000ffff 00000000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000001
"""

UDP = """   sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops
  341: 00000000:A6E1 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 20714 2 0000000000000000 5
  500: 0100007F:1E15 00000000:0000 07 00000000:00000000 00:00000000 00000000  1000        0 81234 2 0000000000000000 {drops}
"""


def snapshot(in_dg=1000, rcvbuf=0, p0=0x58a57, d0=0, drops=0, nic=None):
    s = {"snmp": SNMP.format(in_dg=in_dg, rcvbuf=rcvbuf), "softnet": SOFTNET.format(p0=p0, d0=d0),
         "udp": UDP.format(drops=drops)}
    if nic is not None:
        s["nic"] = {"rx_missed_errors": nic, "rx_fifo_errors": 0, "rx_dropped": 0}
    return s


class Parsers(unittest.TestCase):
    def test_snmp_by_name(self):
        c = parse_snmp_udp(SNMP.format(in_dg=74507, rcvbuf=117))
        self.assertEqual(c["InDatagrams"], 74507)
        self.assertEqual(c["RcvbufErrors"], 117)
        moved = parse_snmp_udp("Udp: RcvbufErrors InDatagrams\nUdp: 4 1\n")
        self.assertEqual((moved["RcvbufErrors"], moved["InDatagrams"]), (4, 1))

    def test_snmp_errors(self):
        with self.assertRaises(ValueError):
            parse_snmp_udp("Ip: 1 2\n")
        with self.assertRaises(ValueError):
            parse_snmp_udp("Udp: A B\nUdp: 1\n")

    def test_softnet_sums_cpus_in_hex(self):
        s = parse_softnet(SOFTNET.format(p0=0x10, d0=0x1f))
        self.assertEqual(s, {"processed": 0x10 + 0xffff, "dropped": 0x1f, "time_squeeze": 3})
        with self.assertRaises(ValueError):
            parse_softnet("")
        with self.assertRaises(ValueError):
            parse_softnet("0000 0000\n")

    def test_socket_by_inode(self):
        self.assertEqual(socket_drops(UDP.format(drops=117), 81234), 117)
        self.assertEqual(socket_drops(UDP.format(drops=117), 20714), 5)
        self.assertIsNone(socket_drops(UDP.format(drops=117), 99))


class Report(unittest.TestCase):
    def test_a_clean_run(self):
        r = report(snapshot(), snapshot(in_dg=6000), 81234)
        self.assertEqual(r["verdict"], "none")
        self.assertEqual((r["backlog"], r["udp_buffers"], r["socket"]), (0, 0, 0))
        self.assertIsNone(r["nic"], "no interface statistics: unknown, not zero")

    def test_the_socket_buffer(self):
        r = report(snapshot(rcvbuf=10, drops=3), snapshot(rcvbuf=60, drops=43), 81234)
        self.assertEqual(r["socket"], 40)
        self.assertEqual(r["udp_buffers"], 50)
        self.assertEqual(r["other_sockets"], 10, "the host's counter includes other sockets")
        self.assertEqual(r["verdict"], "udp_buffers")

    def test_the_first_layer_with_drops_is_the_verdict(self):
        r = report(snapshot(nic=0, rcvbuf=0), snapshot(nic=7, rcvbuf=5, drops=5), 81234)
        self.assertEqual(r["nic"], 7)
        self.assertEqual(r["verdict"], "nic")
        r = report(snapshot(d0=1), snapshot(d0=9, rcvbuf=2, drops=2), 81234)
        self.assertEqual(r["backlog"], 8)
        self.assertEqual(r["verdict"], "backlog")

    def test_32_bit_counters_wrap(self):
        r = report(snapshot(d0=0xFFFFFFFE, drops=4294967290), snapshot(d0=3, drops=4), 81234)
        self.assertEqual(r["backlog"], 5)
        self.assertEqual(r["socket"], 10)

    def test_a_socket_that_is_gone(self):
        before = snapshot()
        after = snapshot()
        after["udp"] = UDP.splitlines()[0] + "\n"
        r = report(before, after, 81234)
        self.assertIsNone(r["socket"])
        self.assertIsNone(r["other_sockets"])


if __name__ == "__main__":
    unittest.main()
