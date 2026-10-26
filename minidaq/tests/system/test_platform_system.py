#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the platform integration (Chapter 25): minidaq_server under a service manager.

The manager here is this test: it binds the notification socket that systemd would name in
NOTIFY_SOCKET and reads what the server sends, as systemd does (sd_notify(3)). Its watchdog is the
check that pings stop when a loop of the server stops; what systemd then does (SIGABRT, a crash
report, a restart) is the server's ordinary crash path of Chapter 21 and systemd's own behavior.
"""
import json
import os
import signal
import socket
import time
import unittest

from systest import SLOW, Ctl, Server, SystemTest, eventually, write_json


class Manager:
    """The service manager's end of the notification socket: an abstract unix datagram socket."""

    def __init__(self):
        self.name = f"@minidaq-systest-{os.getpid()}-{time.monotonic_ns()}"
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind("\0" + self.name[1:])
        self.sock.setblocking(False)
        self.messages = []  # (monotonic time, text)

    def env(self, watchdog_s=None):
        env = {"NOTIFY_SOCKET": self.name}
        if watchdog_s is not None:
            env["WATCHDOG_USEC"] = str(int(watchdog_s * 1e6))
        return env

    def receive(self):
        while True:
            try:
                data = self.sock.recv(4096)
            except BlockingIOError:
                return self.messages
            self.messages.append((time.monotonic(), data.decode()))

    def texts(self):
        return [m for _, m in self.receive()]

    def pings(self):
        return [t for t, m in self.receive() if m == "WATCHDOG=1"]

    def close(self):
        self.sock.close()


def audit_records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class Platform(SystemTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager()
        self.addCleanup(self.manager.close)

    def test_the_server_says_ready_once_it_listens_pings_while_healthy_and_says_stopping(self):
        # REQ: SRS-PLT-001, SRS-PLT-002
        hardware = write_json(self.tmp / "hardware.json", {
            "schema_version": "1.1", "backend": "simulated", "period_ms": 20, "boards": [{"slot": 0}]})
        audit = self.tmp / "audit.jsonl"
        with Server(self.tmp, "--hardware", str(hardware), "--audit", str(audit),
                    env=self.manager.env(watchdog_s=0.4)) as server:
            eventually(lambda: self.manager.texts(), 10, "a message from the server")
            first = self.manager.texts()[0]
            self.assertEqual(first, "READY=1\nSTATUS=state idle")
            Ctl(server).ok("status")  # READY came after the control API was listening
            eventually(lambda: len(self.manager.pings()) >= 10, 30, "ten watchdog pings")
            pings = self.manager.pings()
            gaps = [b - a for a, b in zip(pings, pings[1:])]
            self.assertLess(max(gaps), 0.4 * SLOW, "a gap between pings as long as the interval")
            self.assertEqual(server.stop(), 0, server.output)
        self.assertEqual(self.manager.texts()[-1], "STOPPING=1\nSTATUS=signal 15")
        self.assertNotIn("unhealthy", [r.get("action") for r in audit_records(audit)])

    def test_a_loop_that_hangs_stops_the_pings_and_says_why(self):
        # REQ: SRS-PLT-002
        hardware = write_json(self.tmp / "hardware.json", {
            "schema_version": "1.1", "backend": "simulated", "period_ms": 20,
            "boards": [{"slot": 0, "fault": "hung_bus"}]})
        audit = self.tmp / "audit.jsonl"
        crash = self.tmp / "crash.txt"
        with Server(self.tmp, "--hardware", str(hardware), "--audit", str(audit), "--crash-report", str(crash),
                    env=self.manager.env(watchdog_s=0.4)) as server:
            eventually(lambda: any(m.startswith("STATUS=unhealthy") for m in self.manager.texts()), 30,
                       "the server to report itself unhealthy")
            unhealthy = [m for m in self.manager.texts() if m.startswith("STATUS=unhealthy")][0]
            self.assertEqual(unhealthy[:len("STATUS=unhealthy: slow control")], "STATUS=unhealthy: slow control")
            since = time.monotonic()
            time.sleep(1.0)  # sleep: hides only (a ping in this second would fail the test)
            self.assertEqual([t for t in self.manager.pings() if t > since], [])
            # systemd's next step, after WatchdogSec without a ping: SIGABRT, the crash report.
            self.assertEqual(server.stop(signal.SIGABRT), -signal.SIGABRT)
        records = [r for r in audit_records(audit) if r.get("action") == "unhealthy"]
        self.assertEqual(len(records), 1, records)
        self.assertIn("slow control", records[0]["detail"])
        self.assertIn("SIGABRT", crash.read_text())


if __name__ == "__main__":
    unittest.main()
