#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the front-end hardware (Chapter 22): minidaq_server with --hardware and simulated
boards, driven by minidaq_ctl as an operator would. A simulated board's temperature follows a file
that the test rewrites, as a heat wave or a failed fan would change it.
"""
import subprocess
import unittest

from systest import Ctl, Server, SystemTest, app, eventually, run_config, run_files, write_json

FAULT_SOURCE_HARDWARE = 4  # FaultSource::hardware
HW_CAUSE_TEMPERATURE = 3   # HwFaultCause::temperature


def hardware(directory, temperature_c=25.0):
    """A description of two simulated boards; board 0 follows the file temperature.txt."""
    temperature = directory / "temperature.txt"
    temperature.write_text(f"{temperature_c}\n")
    return write_json(directory / "hardware.json", {
        "schema_version": "1.0",
        "backend": "simulated",
        "period_ms": 20,
        "bias": {"ramp_v_per_s": 50.0},
        "boards": [{"slot": 0, "temperature_file": str(temperature)}, {"slot": 1}],
    }), temperature


class Hardware(SystemTest):
    def test_a_hot_board_stops_the_run_until_it_has_cooled_and_is_acknowledged(self):
        # REQ: SRS-HW-006, SRS-HW-005, SRS-HW-007
        description, temperature = hardware(self.tmp)
        long_run = write_json(self.tmp / "long.json", run_config(self.tmp, prefix="long", rate_hz=1e5, seconds=600))
        with Server(self.tmp, "--hardware", str(description)) as server:
            ctl = Ctl(server)
            ctl.ok("configure", str(long_run))
            eventually(lambda: ctl.status()["hardware"]["ready"], 30, "the boards to ramp up")
            ctl.ok("start")
            temperature.write_text("41.5\n")
            ctl.ok("wait", "fault", "60")
            status = ctl.status()
            self.assertEqual(status["fault"],
                             "hw: board 0 (slot 0): temperature 41.50 C is at or above the alarm limit 40.0 C")
            self.assertEqual([b["state"] for b in status["hardware"]["boards"]], ["fault", "ready"])
            events = [(e["code"], e["a"], e["b"]) for e in ctl.ok("diagnostics", "200")["diagnostics"]["events"]]
            self.assertIn(("hw_fault", 0, HW_CAUSE_TEMPERATURE), events)
            self.assertIn(("fault", status["run_id"], FAULT_SOURCE_HARDWARE), events)

            # A reset while the board is still hot does not hold.
            ctl.ok("reset")
            ctl.ok("wait", "fault", "60")
            temperature.write_text("26.0\n")
            eventually(lambda: ctl.status()["hardware"]["boards"][0]["temperature_c"] == 26.0, 30,
                       "the board to cool down")
            ctl.ok("reset")
            short_run = write_json(self.tmp / "short.json", run_config(self.tmp, prefix="short", seconds=0.2))
            ctl.ok("configure", str(short_run))
            eventually(lambda: ctl.status()["hardware"]["ready"], 30, "the boards to ramp up again")
            ctl.ok("start")
            ctl.ok("wait", "configured", "60")
            self.assertEqual(server.stop(), 0, server.output)
        _, record = run_files(self.tmp, "short")
        boards = record["run"]["hardware"]["boards"]
        self.assertEqual([b["slot"] for b in boards], [0, 1])
        self.assertEqual([b["state"] for b in boards], ["ready", "ready"])
        self.assertAlmostEqual(boards[0]["setpoint_v"], 40.734)  # 38 V + 34 mV/C x 1 C + 2.7 V
        self.assertAlmostEqual(boards[1]["setpoint_v"], 40.7)

    def test_a_board_that_does_not_answer_keeps_the_server_from_starting_a_run(self):
        # REQ: SRS-HW-006, SRS-HW-010
        broken = write_json(self.tmp / "broken.json", {
            "schema_version": "1.0", "boards": [{"slot": 0, "fault": "unresponsive"}]})
        with Server(self.tmp, "--hardware", str(broken)) as server:
            ctl = Ctl(server)
            ctl.ok("wait", "fault", "60")
            self.assertEqual(ctl.status()["fault"], "hw: board 0 (slot 0): no answer in 3 cycles (timeout at 0x000)")
            ctl.ok("reset")
            ctl.ok("configure", str(write_json(self.tmp / "run.json", run_config(self.tmp))))
            code, response, _ = ctl("start")
            self.assertEqual(code, 1)
            self.assertIn(response["error"]["code"], ("device_error", "illegal_transition"))

    def test_a_wrong_description_is_refused_at_start_up(self):
        # REQ: SRS-HW-010
        bad = write_json(self.tmp / "bad.json", {"schema_version": "1.0", "boards": [{"slott": 0}]})
        p = subprocess.run([app("minidaq_server"), "--port", "0", "--hardware", str(bad)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn('/boards/0/slott: unknown key (did you mean "slot"?)', p.stderr)

if __name__ == "__main__":
    unittest.main()
