#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/gate_selftest.py (Chapter 20): its verdicts, and its faults' consistency with
the sources they are planted in. The gates themselves run in CI (job gate-selftest)."""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_selftest as g  # noqa: E402


class Verdict(unittest.TestCase):
    def test_a_gate_that_fails_with_the_planted_reason_caught_it(self):
        self.assertEqual(g.verdict(0, 1, "x.cpp:3: warning: [modernize-use-nullptr]", r"modernize-use-nullptr"), "caught")

    def test_a_fault_the_gate_does_not_notice_is_not_caught(self):
        self.assertEqual(g.verdict(0, 0, "static analysis: clean", r"modernize-use-nullptr"), "NOT CAUGHT")

    def test_a_gate_that_fails_for_another_reason_did_not_catch_the_fault(self):
        self.assertEqual(g.verdict(0, 1, "fatal error: file not found", r"modernize-use-nullptr"),
                         "failed for another reason")

    def test_a_gate_that_fails_on_correct_code_proves_nothing(self):
        self.assertEqual(g.verdict(1, 1, "[modernize-use-nullptr]", r"modernize-use-nullptr"),
                         "gate fails on correct code")


class Faults(unittest.TestCase):
    def test_every_edit_applies_to_exactly_one_place(self):
        for fault in g.FAULTS:
            for path, old, _ in fault.edits:
                with self.subTest(fault=fault.id, path=path):
                    self.assertEqual((g.ROOT / path).read_text().count(old), 1)

    def test_fault_ids_are_unique(self):
        ids = [f.id for f in g.FAULTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_expectation_is_a_valid_pattern(self):
        for fault in g.FAULTS:
            re.compile(fault.expect)


if __name__ == "__main__":
    unittest.main()
