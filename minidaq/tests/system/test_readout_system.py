#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the readout link: minidaq_send plays a readout board (Chapter 19).

minidaq_send simulates singles, cuts them into MDQ-R1 packets, damages the stream on purpose
(loss, reordering, duplicates) and sends it over UDP to minidaq_server, which acquires as it
would from a board. The sender says what it did; the server's counters must account for it
exactly. This is the software half of a hardware-in-the-loop bench: the same tests run against
a real board once the bench has one (Chapter 19).
"""
import re
import subprocess
import unittest

from systest import Ctl, Server, SystemTest, app, eventually, write_json

UDP_PORT = re.compile(r"UDP readout on [\d.]+:(\d+)")
RECEIVE_BUFFER = re.compile(r"receive buffer (\d+) B")
# The receive buffer the acquisition PC is installed with (ADR 0009, Chapter 9). With less, the
# kernel drops datagrams of a burst before the server reads them, and those are losses that no
# sender injected: the tests would measure the machine, not MiniDAQ (MDQ-PR-020).
MIN_RECEIVE_BUFFER = 4 << 20


def udp_config(directory, prefix, **udp):
    return {
        "schema_version": "1.3",
        "description": "system test, UDP readout",
        "source": {"type": "udp", "udp": {"address": "127.0.0.1", "port": 0, **udp}},
        "output": {"type": "listmode", "directory": str(directory), "prefix": prefix},
    }


def send(port, *args):
    """Runs minidaq_send; returns what it reports: singles, packets and the injected damage."""
    p = subprocess.run([app("minidaq_send"), "--port", str(port), *map(str, args)], capture_output=True,
                       text=True, timeout=120)
    if p.returncode != 0:
        raise AssertionError(f"minidaq_send failed: {p.stdout}{p.stderr}")
    out = p.stdout
    report = {"singles": int(re.search(r"singles (\d+)", out).group(1)),
              "packets": int(re.search(r"packets (\d+) of", out).group(1)),
              "lost": 0, "delayed": 0, "duplicated": 0, "both": 0}
    m = re.search(r"injected: lost (\d+), delayed (\d+), duplicated (\d+), both delayed and duplicated (\d+)", out)
    if m:
        report.update(lost=int(m.group(1)), delayed=int(m.group(2)), duplicated=int(m.group(3)),
                      both=int(m.group(4)))
    return report


class Readout(SystemTest):
    def acquire(self, prefix, *send_args, **udp):
        """Configures a UDP run, sends one stream, stops the run; returns (sender report, status)."""
        cfg = write_json(self.tmp / f"{prefix}.json", udp_config(self.tmp, prefix, **udp))
        with Server(self.tmp) as server:
            ctl = Ctl(server)
            ctl.ok("configure", str(cfg))
            ctl.ok("start")
            detector = ctl.status()["detector"]
            port = int(UDP_PORT.search(detector).group(1))
            granted = int(RECEIVE_BUFFER.search(detector).group(1))
            if granted < MIN_RECEIVE_BUFFER:
                self.fail(f"the UDP receive buffer is {granted} B, the readout tests need at least "
                          f"{MIN_RECEIVE_BUFFER} B: set net.core.rmem_max as on the acquisition PC "
                          "(system test plan, section 3)")
            sent = send(port, *send_args)
            expected = sent["packets"] - sent["lost"] + sent["duplicated"]
            eventually(lambda: ctl.status()["detector_counters"]["datagrams"] >= expected, 30,
                       f"{expected} datagrams at the server")
            ctl.ok("stop")
            self.assertEqual(ctl("wait", "configured", "30")[0], 0)
            status = ctl.status()
            self.assertEqual(server.stop(), 0, server.output)
        return sent, status

    def test_a_clean_stream_arrives_complete(self):
        # REQ: SRS-SYS-002, SRS-RDO-012
        sent, status = self.acquire("clean", "--activity", "1e6", "--seconds", "0.5", "--seed", "4", "--speed", "0")
        link = status["detector_counters"]
        self.assertEqual(link["packets_delivered"], sent["packets"])
        self.assertEqual(link["packets_lost"], 0)
        self.assertEqual(link["words_delivered"], sent["singles"])
        self.assertEqual(status["sorter"]["singles_in"], sent["singles"])
        self.assertTrue(status["integrity"]["complete"], status["integrity"])

    # [snippet:damaged]
    def check_accounting(self, sent, status):
        link = status["detector_counters"]
        self.maxDiff = None
        context = f"sent {sent}, link {link}"
        # A delayed packet is either put back in order (reordered) or arrives after its gap was
        # given up: then it was counted lost, and is dropped as stale when it comes. One that was
        # also duplicated had its copy sent on time, so it is a duplicate, not late (MDQ-PR-018).
        too_late = sent["delayed"] - sent["both"] - link["packets_reordered"]
        self.assertGreaterEqual(too_late, 0, context)
        self.assertEqual(link["packets_lost"], sent["lost"] + too_late, context)
        self.assertEqual(link["packets_stale"], sent["duplicated"] + too_late, context)
        self.assertEqual(link["packets_delivered"] + link["packets_lost"], sent["packets"], context)
        self.assertEqual(link["packets_received"], link["packets_delivered"] + link["packets_stale"], context)
        # The run is marked incomplete, with the loss counter named.
        self.assertFalse(status["integrity"]["complete"])
        self.assertIn("/detector_counters/packets_lost", [x["counter"] for x in status["integrity"]["losses"]])

    def test_every_damaged_packet_is_accounted_for(self):
        # REQ: SRS-SYS-002, SRS-RDO-007, SRS-CTL-030
        sent, status = self.acquire("damaged", "--activity", "1e6", "--seconds", "0.5", "--seed", "5",
                                    "--loss", "0.01", "--reorder", "0.01", "--duplicate", "0.01", "--speed", "1")
        self.assertGreater(sent["lost"] * sent["delayed"] * sent["duplicated"], 0, sent)
        self.check_accounting(sent, status)

    def test_a_packet_both_delayed_and_duplicated_is_a_duplicate(self):
        # REQ: SRS-SYS-002, SRS-RDO-007
        # 5% of each kind of damage: some packets are delayed and duplicated at once.
        sent, status = self.acquire("heavy", "--activity", "1e6", "--seconds", "0.5", "--seed", "8",
                                    "--loss", "0.05", "--reorder", "0.05", "--duplicate", "0.05", "--speed", "1")
        self.assertGreater(sent["both"], 0, sent)
        self.check_accounting(sent, status)
    # [/snippet:damaged]

    def test_the_sequence_number_wraps_without_loss(self):
        # REQ: SRS-SYS-002, SRS-RDO-003
        sent, status = self.acquire("wrap", "--activity", "1e6", "--seconds", "0.2", "--seed", "6", "--speed", "0",
                                    "--first-sequence", str(2**32 - 100))
        link = status["detector_counters"]
        self.assertGreater(sent["packets"], 100, "the stream must cross the wrap")
        self.assertEqual(link["packets_delivered"], sent["packets"])
        self.assertEqual(link["packets_lost"] + link["sequence_resyncs"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
