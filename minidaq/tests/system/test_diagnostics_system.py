#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the diagnostics (Chapter 21): the flight recorder seen through minidaq_ctl,
and a server that crashes, its crash report and its core dump.

The crash is a SIGSEGV sent with kill, the one way to crash the shipped program from outside
without a test-only command in it. The handler treats it like a fault: it writes the report and
dies of the signal. Whether a core file appears depends on the machine (kernel.core_pattern and
the core size limit): where the pattern is a plain file name, the test also runs
tools/postmortem.sh on the core; elsewhere (a pipe to systemd-coredump or apport) it says so and
checks the report only. Sanitizer builds handle fatal signals themselves; the crash test does
not run there.
"""
import os
import pathlib
import re
import signal
import subprocess
import unittest

from systest import Ctl, Server, SystemTest, app, run_config, write_json

ROOT = pathlib.Path(__file__).resolve().parents[3]


def build_id(path):
    out = subprocess.run(["readelf", "-n", str(path)], capture_output=True, text=True).stdout
    m = re.search(r"Build ID: ([0-9a-f]+)", out)
    return m.group(1) if m else None


def plain_core_pattern():
    """The core file name if kernel.core_pattern writes a file in the process's directory."""
    try:
        pattern = pathlib.Path("/proc/sys/kernel/core_pattern").read_text().strip()
    except OSError:
        return None
    return pattern if pattern and not pattern.startswith("|") and "/" not in pattern else None


class Diagnostics(SystemTest):
    def test_the_client_shows_what_the_server_did_last(self):
        # REQ: SRS-DIAG-003, SRS-DIAG-004
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp, seconds=0.2))
        with Server(self.tmp) as server:
            ctl = Ctl(server)
            status = ctl.run(cfg)
            d = ctl.ok("diagnostics", "200")["diagnostics"]
            self.assertEqual(d["build_id"], build_id(app("minidaq_server")))
            events = [(e["code"], e["a"], e["b"]) for e in d["events"]]
            self.assertIn(("run_begin", status["run_id"], 0), events)
            self.assertIn(("run_end", status["run_id"], 1), events)
            code, _, err = ctl("diagnostics", "2000")
            self.assertEqual(code, 2, "the client checks the count before it asks")
            self.assertIn("0 to 1024", err)

    @unittest.skipIf(os.environ.get("MINIDAQ_SANITIZED"), "sanitizers handle fatal signals themselves")
    def test_a_crashed_server_leaves_a_report_and_dies_of_the_signal(self):
        # REQ: SRS-DIAG-002
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp, seconds=0.2))
        report = self.tmp / "crash.txt"
        with Server(self.tmp, "--crash-report", str(report), core_dumps=True) as server:
            status = Ctl(server).run(cfg)
            code = server.stop(signal.SIGSEGV)
        self.assertEqual(code, -signal.SIGSEGV, f"killed by the signal, not an exit: {server.output}")
        text = report.read_text()
        self.assertTrue(text.startswith("MiniDAQ crash report\n"), text)
        self.assertIn(f"signal: SIGSEGV (11) sent by pid {os.getpid()}\n", text)
        self.assertIn(f"build-id: {build_id(app('minidaq_server'))}\n", text)
        self.assertRegex(text, rf"\n\d+ \d+ \d+ run_end {status['run_id']} 1\n")
        self.assertTrue(text.endswith("end of report\n"), text)

        pattern = plain_core_pattern()
        cores = sorted(self.tmp.glob("core*")) if pattern else []
        if not cores:
            print(f"no core file here (core_pattern {pattern or 'not a file name'}): report checked only")
            return
        p = subprocess.run([str(ROOT / "tools/postmortem.sh"), str(cores[0]), app("minidaq_server")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Program terminated with signal SIGSEGV", p.stdout)
        self.assertIn("in main", p.stdout, "the main thread's stack, with symbols")


if __name__ == "__main__":
    unittest.main()
