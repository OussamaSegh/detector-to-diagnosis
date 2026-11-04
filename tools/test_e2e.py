#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/e2e.py (Chapter 33), run by CTest as tools.e2e.

The accounting checks on a consistent set of counters, and on the same set with one counter off
by one: each such change must fail at least one check, or the checks would not see that stage
lose or invent a count. With the programs' directory as argument, a short end-to-end run as well
(without the reconstruction): a clean link must give the reference's records, a damaged one an
incomplete run with every packet accounted for.

    python3 tools/test_e2e.py [build/debug/minidaq/apps]
"""
import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e2e  # noqa: E402

APPS = None

SENT = {"singles": 1000, "packets": 10, "lost": 0, "delayed": 0, "duplicated": 0, "both": 0}
STATUS = {
    "detector_counters": {"packets_delivered": 10, "packets_lost": 0, "packets_received": 10,
                          "packets_stale": 0, "words_delivered": 1000},
    "sorter": {"singles_in": 1000, "energy_rejected": 498, "out_of_order": 2, "singles_alone": 370,
               "pair_windows": 62, "singles_in_multiples": 6, "prompts": 60,
               "geometry_rejected": 2, "delayed": 5},
    "sink_counters": {"coincidences": 65},
    "integrity": {"complete": True, "losses": []},
}
RECORDS = (60, 5)
SINO = {"prompts": 58, "delayeds": 4, "outside_fov": 3, "above_mrd": 0, "tof_outside": 0,
        "no_angle": 0, "invalid": 0}


def failed(sent=SENT, status=STATUS, records=RECORDS, sino=SINO):
    return [c["name"] for c in e2e.accounting(sent, status, records, sino) if not c["ok"]]


class Accounting(unittest.TestCase):
    def test_consistent_counters_pass_every_check(self):
        # REQ: SRS-SYS-007
        self.assertEqual(failed(), [])

    def test_every_counter_off_by_one_fails_a_check(self):
        # REQ: SRS-SYS-007
        for section in ("detector_counters", "sorter", "sink_counters"):
            for key in STATUS[section]:
                for delta in (-1, 1):
                    status = copy.deepcopy(STATUS)
                    status[section][key] += delta
                    with self.subTest(counter=f"{section}/{key}", delta=delta):
                        self.assertNotEqual(failed(status=status), [])
        for key in SINO:
            sino = dict(SINO, **{key: SINO[key] + 1})
            with self.subTest(sinogram=key):
                self.assertNotEqual(failed(sino=sino), [])
        for i in range(2):
            records = list(RECORDS)
            records[i] += 1
            with self.subTest(records=i):
                self.assertNotEqual(failed(records=tuple(records)), [])
        for key in ("singles", "packets"):
            with self.subTest(sent=key):
                self.assertNotEqual(failed(sent=dict(SENT, **{key: SENT[key] + 1})), [])

    def test_a_clean_run_that_says_it_is_incomplete_fails(self):
        status = copy.deepcopy(STATUS)
        status["integrity"]["complete"] = False
        self.assertEqual(failed(status=status), ["integrity: the run says whether it is complete"])

    def test_a_damaged_link_is_checked_by_its_balance_not_by_equality(self):
        # REQ: SRS-SYS-007
        sent = dict(SENT, lost=1)
        status = copy.deepcopy(STATUS)
        status["detector_counters"].update(packets_delivered=9, packets_lost=1, packets_received=9,
                                           words_delivered=900)
        status["sorter"].update(singles_in=900, energy_rejected=398)
        status["integrity"]["complete"] = False
        self.assertEqual(failed(sent=sent, status=status), [])
        status["integrity"]["complete"] = True
        self.assertEqual(failed(sent=sent, status=status),
                         ["integrity: the run says whether it is complete"])


class Parsing(unittest.TestCase):
    def test_the_sinogram_summary_is_read(self):
        text = ("binned 13038 prompts, 142 delayeds; outside the FOV 195, above the ring difference "
                "0, outside the TOF range 0, no angle 0, invalid 0\n")
        self.assertEqual(e2e.parse_sino(text)["outside_fov"], 195)
        with self.assertRaises(ValueError):
            e2e.parse_sino("binned 3 prompts")

    def test_the_senders_report_is_read(self):
        text = ("singles 912139 in 2 s of detector time (1e+06 Bq)\npackets 5012 of up to 182 words\n"
                "injected: lost 10, delayed 9, duplicated 8, both delayed and duplicated 1\n")
        self.assertEqual(e2e.parse_send(text), {"singles": 912139, "packets": 5012, "lost": 10,
                                                "delayed": 9, "duplicated": 8, "both": 1})


@unittest.skipIf(APPS is None and len(sys.argv) < 2, "no programs given")
class EndToEnd(unittest.TestCase):
    def run_e2e(self, *extra):
        with tempfile.TemporaryDirectory(prefix="minidaq-e2e-test-") as tmp:
            out = pathlib.Path(tmp) / "out"
            code = e2e.main([str(APPS), str(out), "--seconds", "0.5", "--activity", "2e6",
                             "--speed", "0", "--no-image", "--quiet", *extra])
            result = json.loads((out / "e2e.json").read_text())
            manifest = json.loads((out / "manifest.json").read_text())
        return code, result, manifest

    def test_a_clean_link_gives_the_reference_records_and_every_count_adds_up(self):
        # REQ: SRS-SYS-006, SRS-SYS-007
        code, result, manifest = self.run_e2e()
        bad = [(a["name"], c) for a in result["acquisitions"] for c in a["checks"] if not c["ok"]]
        self.assertEqual(bad, [])
        self.assertEqual(code, 0)
        for acq in result["acquisitions"]:
            names = [c["name"] for c in acq["checks"]]
            self.assertIn("reference: the server wrote the reference's records", names)
        self.assertIn("qc/report.json", manifest)
        self.assertIn("phantom.run.json", manifest)

    def test_a_damaged_link_gives_an_incomplete_run_with_every_packet_accounted_for(self):
        # REQ: SRS-SYS-007, SRS-SYS-002
        code, result, _ = self.run_e2e("--loss", "0.005", "--duplicate", "0.005")
        phantom = result["acquisitions"][1]
        self.assertGreater(phantom["sent"]["lost"], 0)
        checks = {c["name"]: c for c in phantom["checks"]}
        self.assertNotIn("reference: the server wrote the reference's records", checks)
        self.assertTrue(checks["link: delivered or lost"]["ok"])
        self.assertTrue(checks["integrity: the loss is named"]["ok"])
        self.assertEqual(checks["integrity: the run says whether it is complete"]["left"], False)
        # every other check must balance too: a damaged link changes the equations, not the rule
        # that each of them holds
        bad = [(a["name"], c["name"]) for a in result["acquisitions"] for c in a["checks"]
               if not c["ok"]]
        self.assertEqual(bad, [])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        APPS = pathlib.Path(sys.argv.pop(1)).resolve()
        os.environ.setdefault("MINIDAQ_APPS", str(APPS))
    unittest.main()
