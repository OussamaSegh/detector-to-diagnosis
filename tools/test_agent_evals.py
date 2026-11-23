#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the subagent evals (tools/agent_evals/, CR-0036): the scorer's matching rules, and
that every case names its findings and a patch on files of the eval's base commit (the test
tools.agent_gate applies the known-bad library's patches)."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/agent_evals"))
import score  # noqa: E402

CASES = ROOT / "tools/agent_evals/trace-review/cases.json"
CASE = {"id": "x", "expected": [{"finding": 1, "mentions": ["SRS-CFG-001"]},
                                {"finding": 3, "mentions": ["SRS-SRT-009", "RC-03"]}]}


class Scoring(unittest.TestCase):
    def test_each_expected_finding_is_matched_by_number_and_mentions(self):
        report = ("1. SRS-CFG-001 has no test left (test_config.cpp:38).\n"
                  "**3)** The accounting of SRS-SRT-009, risk control RC-03, is loosened.\n")
        results, ok = score.score(CASE, report)
        self.assertTrue(ok, results)
        self.assertEqual([v for v, _ in results], ["FOUND", "FOUND"])

    def test_the_wrong_number_or_a_missing_mention_is_a_miss(self):
        report = "2. SRS-CFG-001 has no test left.\n3. SRS-SRT-009 is loosened.\n"
        results, ok = score.score(CASE, report)
        self.assertFalse(ok)
        self.assertEqual([v for v, _ in results], ["MISSED", "MISSED", "EXTRA", "EXTRA"])

    def test_other_numbering_forms_are_read(self):
        for line in ["Finding 1: SRS-CFG-001", "[1] SRS-CFG-001", "- 1. SRS-CFG-001",
                     "  1) SRS-CFG-001"]:
            self.assertEqual(score.numbered(line), [(1, line)], line)
        self.assertEqual(score.numbered("In 2026 nothing.\nSRS-CFG-001 1. late"), [])

    def test_a_case_without_findings_needs_no_findings_and_no_numbers(self):
        none = {"id": "g", "expected": "none"}
        self.assertTrue(score.score(none, "No findings. I read srs.md and the diff.")[1])
        self.assertFalse(score.score(none, "No findings.\n2. A test without a tag.")[1])
        self.assertFalse(score.score(none, "The change looks fine.")[1])


class Cases(unittest.TestCase):
    def test_every_case_patch_changes_files_of_the_base(self):
        spec = json.loads(CASES.read_text())
        if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", spec["base"] + "^{commit}"],
                          capture_output=True).returncode != 0:
            self.skipTest("the eval's base commit is not in this clone")
        self.assertTrue((ROOT / spec["agent"]).is_file() or not (ROOT / ".claude").exists())
        for case in spec["cases"]:
            with self.subTest(case=case["id"]):
                patch = (ROOT / case["patch"]).read_text()
                files = [line[6:] for line in patch.splitlines() if line.startswith("--- a/")]
                for f in files:
                    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{spec['base']}:{f}"],
                                       capture_output=True)
                    self.assertEqual(r.returncode, 0, f"{f} is not in the base")
                self.assertTrue(case["expected"] == "none" or case["expected"])


if __name__ == "__main__":
    unittest.main()
