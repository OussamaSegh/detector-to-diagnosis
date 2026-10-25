#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of an acquisition, from the operator's command to the files (Chapter 19).

Three kinds of check, from strict to statistical:

- accounting: every coincidence the server counts is in the files, and the run record says
  what the status said;
- golden data, exact: a seeded run gives the same records every time and in every build, and
  those records are the ones in golden/seed1.json, so any change to what the DAQ writes shows;
- golden data, statistical: a run with another seed is not equal to the golden run, but its
  spectrum and rates must not differ from it by more than chance explains.

    MINIDAQ_APPS=build/debug/minidaq/apps python3 minidaq/tests/system/test_acquisition_system.py
    ... test_acquisition_system.py --update-golden   # after a reviewed change of the output
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest

import stats
from systest import Ctl, Server, SystemTest, app, read_listmode, run_config, run_files, write_json

GOLDEN = pathlib.Path(__file__).with_name("golden") / "seed1.json"
SIGNIFICANCE = 1e-3  # a false alarm in one run of a thousand; see Chapter 19 on choosing it
ENERGY_BINS = (435.0, 585.0, 30)
DT_BINS = (-4000.0, 4000.0, 40)


def acquire(test, prefix, seed, seconds=1.0, **sections):
    """Runs one synthetic acquisition through server and client; returns (status, files, record)."""
    cfg = write_json(test.tmp / f"{prefix}.json",
                     run_config(test.tmp, prefix=prefix, seed=seed, seconds=seconds, **sections))
    with Server(test.tmp) as server:
        status = Ctl(server).run(cfg)
        test.assertEqual(server.stop(), 0, server.output)
    files, record = run_files(test.tmp, prefix)
    verify = subprocess.run([app("minidaq_listmode"), "verify", *map(str, files)], capture_output=True,
                            text=True)
    test.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
    return status, files, record


# [snippet:summary]
def summarize(files):
    """What the golden file keeps of a run: counts, a digest of every record, and histograms."""
    digest = hashlib.sha256()
    prompts = delayed = 0
    energies, dts = [], []
    for rec in read_listmode(files):
        digest.update(repr(rec).encode())
        if rec[3]:
            delayed += 1
        else:
            prompts += 1
            energies += (rec[5], rec[6])
            dts.append(rec[4])
    return {
        "prompts": prompts,
        "delayed": delayed,
        "sha256": digest.hexdigest(),
        "energy_kev": stats.histogram(energies, *ENERGY_BINS),
        "dt_ps": stats.histogram(dts, *DT_BINS),
    }
# [/snippet:summary]


class Accounting(SystemTest):
    def test_every_coincidence_counted_is_in_the_files(self):
        # REQ: SRS-SYS-001, SRS-OUT-009, SRS-OUT-010
        status, files, record = acquire(self, "acc", seed=3, seconds=1.0)
        s = summarize(files)
        sorter, sink = status["sorter"], status["sink_counters"]
        self.assertEqual(sorter["singles_in"], 1_000_000)
        self.assertEqual(s["prompts"], sorter["prompts"])
        self.assertEqual(s["delayed"], sorter["delayed"])
        self.assertEqual(s["prompts"] + s["delayed"], sink["coincidences"])
        # The stages account for every single: what the pair stage did not filter it passed on.
        stages = {st["name"]: st for st in status["stages"]}
        self.assertEqual(stages["source"]["out"], stages["pair"]["in"])
        self.assertEqual(stages["pair"]["out"], sink["coincidences"])
        self.assertTrue(status["integrity"]["complete"])
        # The run record holds the service's status as the run ended, and the sink's own counters
        # after it closed the files; only the fsync of the record itself is missing from them.
        for key in ("sorter", "stages", "integrity", "run_id", "config"):
            self.assertEqual(record["run"][key], status[key], key)
        final = dict(status["sink_counters"], fsyncs=status["sink_counters"]["fsyncs"] - 1)
        self.assertEqual(record["sink_counters"], final)
        self.assertEqual(record["files"], [f.name for f in files])


class GoldenExact(SystemTest):
    def test_a_seeded_run_writes_the_golden_records(self):
        # REQ: SRS-SYS-004
        golden = json.loads(GOLDEN.read_text())
        _, files, _ = acquire(self, "gold", seed=1, seconds=1.0)
        s = summarize(files)
        self.assertEqual((s["prompts"], s["delayed"]), (golden["prompts"], golden["delayed"]))
        self.assertEqual(s["sha256"], golden["sha256"],
                         "the records differ from the golden run: if the change is intended, review "
                         "it and run this file with --update-golden")

    def test_batch_sizes_and_delays_do_not_change_the_records(self):
        # REQ: SRS-SYS-004, SRS-SRT-008
        _, files, _ = acquire(self, "small", seed=1, seconds=1.0,
                              pipeline={"batch_size": 257, "max_batch_delay_us": 50})
        self.assertEqual(summarize(files)["sha256"], json.loads(GOLDEN.read_text())["sha256"])


class GoldenStatistical(SystemTest):
    def compare(self, s, golden):
        """The p-values of the comparisons of run summary s with the golden summary."""
        return {
            "prompt rate": stats.poisson_rates_equal(s["prompts"], 1.0, golden["prompts"], 1.0),
            "delayed rate": stats.poisson_rates_equal(s["delayed"], 1.0, golden["delayed"], 1.0),
            "energy spectrum": stats.chi2_homogeneity(s["energy_kev"], golden["energy_kev"])[2],
            "time differences": stats.chi2_homogeneity(s["dt_ps"], golden["dt_ps"])[2],
        }

    def test_another_seed_agrees_with_the_golden_run_within_chance(self):
        # REQ: SRS-SYS-005
        golden = json.loads(GOLDEN.read_text())
        _, files, _ = acquire(self, "seed2", seed=2, seconds=1.0)
        s = summarize(files)
        self.assertNotEqual(s["sha256"], golden["sha256"], "another seed must give other records")
        for what, p in self.compare(s, golden).items():
            self.assertGreater(p, SIGNIFICANCE, f"{what} differs from the golden run (p = {p:.2g})")

    def test_the_comparison_finds_a_narrower_energy_window(self):
        # A negative control: the comparison must fail for a run that is really different. An
        # energy window 5 keV narrower on each side removes about 3% of the singles' spectrum.
        golden = json.loads(GOLDEN.read_text())
        _, files, _ = acquire(self, "narrow", seed=2, seconds=1.0,
                              sorter={"energy_low_kev": 440.0, "energy_high_kev": 580.0})
        p = self.compare(summarize(files), golden)
        self.assertLess(p["energy spectrum"], SIGNIFICANCE, p)


def update_golden():
    """Writes golden/seed1.json from a run of the current build. Review the diff before committing."""
    class Once(SystemTest):
        def runTest(self):
            _, files, _ = acquire(self, "gold", seed=1, seconds=1.0)
            GOLDEN.parent.mkdir(exist_ok=True)
            write_json(GOLDEN, {"description": "run_config(seed=1, seconds=1.0) through minidaq_server; "
                                               "see test_acquisition_system.py", **summarize(files)})
    result = unittest.TextTestRunner().run(Once())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    if "--update-golden" in sys.argv:
        sys.exit(update_golden())
    unittest.main(verbosity=1)
