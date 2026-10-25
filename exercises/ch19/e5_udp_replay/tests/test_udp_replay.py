# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 19.5. Run by CTest, which puts the starter or solution directory
on PYTHONPATH and sets MINIDAQ_APPS to the directory of MiniDAQ's programs. The helpers of
MiniDAQ's system tests (minidaq/tests/system/systest.py) start the server and the client."""
import os
import pathlib
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "minidaq/tests/system"))

import systest  # noqa: E402
import udp_replay  # noqa: E402


def receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    sock.bind(("127.0.0.1", 0))
    return sock


class Recording(threading.Thread):
    """udp_replay.record() on a socket of its own, in the background."""

    def __init__(self, path, idle_s=0.5):
        super().__init__(daemon=True)
        self.sock = receiver()
        self.port = self.sock.getsockname()[1]
        self.path, self.idle_s, self.count, self.error = path, idle_s, None, None
        self.start()

    def run(self):
        try:
            self.count = udp_replay.record(self.sock, self.path, idle_s=self.idle_s, timeout_s=30 * systest.SLOW)
        except Exception as e:  # reported by finish()
            self.error = e
        finally:
            self.sock.close()

    def finish(self):
        self.join(60 * systest.SLOW)
        if self.is_alive() or self.error:
            raise AssertionError(f"record() did not finish: {self.error}")
        return self.count


def drain(sock, n, seconds=10):
    sock.settimeout(seconds * systest.SLOW)
    return [sock.recv(65535) for _ in range(n)]


class CaptureFile(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ex19-5-"))

    def write(self, payloads, gap_s=0.0):
        rec = Recording(self.tmp / "c.cap", idle_s=0.3 + gap_s)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            for i, p in enumerate(payloads):
                if i and gap_s:
                    time.sleep(gap_s)  # sleep: device (a link with gaps between datagrams)
                s.sendto(p, ("127.0.0.1", rec.port))
        self.assertEqual(rec.finish(), len(payloads))
        return self.tmp / "c.cap"

    def test_a_recording_reads_back_in_order(self):
        payloads = [bytes([i % 256]) * (1 + 37 * i % 1400) for i in range(200)]
        records = udp_replay.read_capture(self.write(payloads))
        self.assertEqual([p for _, p in records], payloads)
        offsets = [t for t, _ in records]
        self.assertEqual(offsets[0], 0)
        self.assertEqual(offsets, sorted(offsets))

    def test_the_file_format_is_mdq_cap1(self):
        path = self.write([b"abc", b"de"])
        blob = path.read_bytes()
        self.assertEqual(blob[:8], b"MDQCAP1\n")
        offset, length = struct.unpack_from("<QI", blob, 8)
        self.assertEqual((offset, length, blob[20:23]), (0, 3, b"abc"))
        self.assertEqual(len(blob), 8 + 12 + 3 + 12 + 2)

    def test_a_damaged_capture_is_refused(self):
        blob = self.write([b"abc", b"defgh"]).read_bytes()
        for bad in (b"MDQCAP0\n" + blob[8:], blob[:-1], blob[:-6]):
            path = self.tmp / "bad.cap"
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                udp_replay.read_capture(path)

    def test_record_fails_when_nothing_arrives(self):
        with receiver() as sock, self.assertRaises(TimeoutError):
            udp_replay.record(sock, self.tmp / "empty.cap", idle_s=0.1, timeout_s=0.2)


class Replay(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ex19-5-"))
        self.cap = self.tmp / "gaps.cap"
        with open(self.cap, "wb") as f:  # three datagrams 0.2 s apart, written by hand
            f.write(b"MDQCAP1\n")
            for i, t in enumerate((0, 200_000_000, 400_000_000)):
                f.write(struct.pack("<QI", t, 1) + bytes([i]))

    def replay_time(self, speed):
        with receiver() as sock:
            start = time.monotonic()
            self.assertEqual(udp_replay.replay(self.cap, "127.0.0.1", sock.getsockname()[1], speed), 3)
            self.assertEqual(drain(sock, 3), [b"\x00", b"\x01", b"\x02"])
            return time.monotonic() - start

    def test_speed_one_keeps_the_gaps(self):
        self.assertGreaterEqual(self.replay_time(1.0), 0.39)

    def test_speed_two_halves_them(self):
        self.assertGreaterEqual(self.replay_time(2.0), 0.19)
        self.assertLess(self.replay_time(2.0), 0.39 * systest.SLOW)

    def test_speed_zero_does_not_wait(self):
        self.assertLess(self.replay_time(0.0), 0.15 * systest.SLOW)


UDP_PORT = re.compile(r"UDP readout on [\d.]+:(\d+)")


class AgainstTheServer(systest.SystemTest):
    """A damaged stream from minidaq_send, recorded once and replayed twice into minidaq_server."""

    def acquire(self, prefix, capture):
        cfg = systest.write_json(self.tmp / f"{prefix}.json", {
            "schema_version": "1.3", "description": "Exercise 19.5, a replayed capture",
            # A gap is given up after the reorder window, not after a time (see the README).
            "source": {"type": "udp", "udp": {"address": "127.0.0.1", "port": 0, "max_hold_us": 1_000_000}},
            "output": {"type": "listmode", "directory": str(self.tmp), "prefix": prefix}})
        n = len(udp_replay.read_capture(capture))
        with systest.Server(self.tmp) as server:
            ctl = systest.Ctl(server)
            ctl.ok("configure", str(cfg))
            ctl.ok("start")
            port = int(UDP_PORT.search(ctl.status()["detector"]).group(1))
            udp_replay.replay(capture, "127.0.0.1", port, speed=1.0)
            systest.eventually(lambda: ctl.status()["detector_counters"]["datagrams"] >= n, 30,
                               f"{n} datagrams at the server")
            ctl.ok("stop")
            self.assertEqual(ctl("wait", "configured", "30")[0], 0)
            status = ctl.status()
            self.assertEqual(server.stop(), 0, server.output)
        records = list(systest.read_listmode(systest.run_files(self.tmp, prefix)[0]))
        # receive_batches counts the server's reads of its socket, which depend on timing: it
        # describes the server, not the data.
        link = {k: v for k, v in status["detector_counters"].items() if k != "receive_batches"}
        return link, status["sorter"], records

    def test_a_replay_gives_the_same_run_every_time(self):
        capture = self.tmp / "damaged.cap"
        rec = Recording(capture)
        out = subprocess.run([systest.app("minidaq_send"), "--port", str(rec.port), "--activity", "1e6",
                              "--seconds", "0.3", "--seed", "5", "--loss", "0.01", "--reorder", "0.01",
                              "--duplicate", "0.01", "--speed", "1"], capture_output=True, text=True,
                             timeout=120).stdout
        count = rec.finish()
        packets = int(re.search(r"packets (\d+) of", out).group(1))
        lost, _, duplicated = map(int, re.search(r"injected: lost (\d+), delayed (\d+), duplicated (\d+)",
                                                 out).groups())
        self.assertEqual(count, packets - lost + duplicated, "the recording itself lost datagrams")

        first = self.acquire("first", capture)
        second = self.acquire("second", capture)
        self.assertEqual(first[0], second[0], "the link's counters differ between replays")
        self.assertEqual(first[1], second[1], "the sorter's counters differ between replays")
        self.assertEqual(first[2], second[2], "the records differ between replays")
        self.assertGreater(first[0]["packets_lost"], 0, "the replay must carry the recorded damage")
        self.assertGreater(len(first[2]), 0)


if __name__ == "__main__":
    unittest.main()
