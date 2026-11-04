#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/req_baseline.py (Chapter 33), run by CTest as tools.req_baseline.

A small SRS, its baseline and a few change requests in a temporary tree: an unchanged SRS passes;
a requirement added, changed in one word, or removed fails until an approved or implemented change
request names it; a proposed or rejected request does not count; rewrapping a row changes nothing.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import req_baseline as rb  # noqa: E402

SRS = """# SRS

Version 3.

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-ABC-001 | The thing shall count every single. | core | T |
| SRS-ABC-002 | The thing shall write 3 files. | output | T |
| SRS-ABC-003 | The thing shall not crash. | core | T, I |
"""
CR = """# CR-{n}: Something

| Field | Value |
|---|---|
| Status | {status} |

## Impact analysis

{body}
"""


class Freeze(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        (self.root / rb.CHANGES).mkdir(parents=True)
        self.srs(SRS)
        self.assertEqual(rb.main([str(self.root), "--write", "test baseline"]), 0)

    def tearDown(self):
        self._tmp.cleanup()

    def srs(self, text):
        (self.root / rb.SRS).write_text(text)

    def cr(self, n, status, body):
        (self.root / rb.CHANGES / f"CR-{n}-x.md").write_text(CR.format(n=n, status=status, body=body))

    def problems(self):
        return rb.check(self.root)[0]

    def test_an_unchanged_srs_passes(self):
        self.assertEqual(self.problems(), [])
        base = json.loads((self.root / rb.BASELINE).read_text())
        self.assertEqual(base["srs_version"], 3)
        self.assertEqual(sorted(base["requirements"]), ["SRS-ABC-001", "SRS-ABC-002", "SRS-ABC-003"])

    def test_rewrapping_or_spacing_a_row_changes_nothing(self):
        self.srs(SRS.replace("| The thing shall write 3 files. |", "|  The thing shall write  3 files.   |"))
        self.assertEqual(self.problems(), [])

    def test_a_changed_word_an_item_or_a_method_needs_a_change_request(self):
        for old, new in (("write 3 files", "write 4 files"), ("| output |", "| core |"),
                         ("| T, I |", "| T |")):
            with self.subTest(new):
                self.srs(SRS.replace(old, new))
                p = self.problems()
                self.assertEqual(len(p), 1, p)
                self.assertIn("changed since the baseline", p[0])

    def test_an_added_or_removed_requirement_needs_a_change_request(self):
        self.srs(SRS + "| SRS-ABC-004 | The thing shall stop. | core | T |\n")
        self.assertIn("SRS-ABC-004 added", self.problems()[0])
        self.srs(SRS.replace("| SRS-ABC-002 | The thing shall write 3 files. | output | T |\n", ""))
        self.assertIn("SRS-ABC-002 removed", self.problems()[0])

    def test_only_an_approved_or_implemented_request_that_names_it_counts(self):
        self.srs(SRS.replace("write 3 files", "write 4 files"))
        self.cr("0001", "proposed", "Changes SRS-ABC-002.")
        self.cr("0002", "rejected", "Changes SRS-ABC-002.")
        self.cr("0003", "implemented", "Changes SRS-ABC-001 only.")
        self.assertEqual(len(self.problems()), 1)
        self.cr("0004", "approved", "Changes SRS-ABC-002 to four files.")
        self.assertEqual(self.problems(), [])
        rows = rb.check(self.root)[1]
        self.assertEqual(rows, [("SRS-ABC-002", "changed", ["CR-0004"])])

    def test_a_new_baseline_clears_the_differences(self):
        self.srs(SRS + "| SRS-ABC-004 | The thing shall stop. | core | T |\n")
        self.assertEqual(len(self.problems()), 1)
        rb.main([str(self.root), "--write", "after review"])
        self.assertEqual(self.problems(), [])


if __name__ == "__main__":
    unittest.main()
