#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/release_record.py (roadmap 2.0.0, Theme D)."""
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_record as rr  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = """## part 1
pass  build and tests, six presets
pass  static analysis
FAIL  starters fail
1 release checks failed (part 1)
## part 1
pass  build and tests, six presets
pass  static analysis
pass  starters fail
all release checks passed (part 1)
## part 4
pass  fuzz build
pass  fuzz_config, 600 s
FAIL  fuzz_decoder, 600 s
"""


class ReleaseRecord(unittest.TestCase):
    def test_a_part_run_again_replaces_its_earlier_result(self):
        found = rr.results(CHECKS)
        self.assertEqual(found["starters fail"], "pass")
        self.assertEqual(rr.row_result(found, ["starters fail"]), "pass")
        self.assertEqual(rr.row_result(found, ["fuzz_", "fuzz build"]), "FAIL")
        self.assertEqual(rr.row_result(found, ["soak"]), "not run")

    def test_the_skeleton_of_a_release_has_every_row_and_fails_the_check_until_filled(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            shutil.copytree(ROOT / "docs/regulatory", root / "docs/regulatory")
            shutil.copytree(ROOT / "exercises/ch14/e5_release_check", root / "exercises/ch14/e5_release_check")
            ev = root / "measurements/release-9.9.0"
            ev.mkdir(parents=True)
            (ev / "commit.txt").write_text("commit " + "a" * 40 + "\n")
            (ev / "release-checks.txt").write_text(CHECKS)
            text = rr.skeleton(root, "9.9.0")
            self.assertIn("MiniDAQ 9.9.0, commit " + "a" * 40 + ", tag book-v9.9.0", text)
            for name, _, _ in rr.ROWS:
                self.assertIn(f"| {name} |", text)
            self.assertIn("| fuzzing | FAIL |", text)
            self.assertIn("| soak, 30 minutes | not run |", text)
            record = root / "docs/regulatory/releases/9.9.0.md"
            record.write_text(text)
            errors = rr.check(root, record)
            self.assertTrue(any("TODO(record)" in e for e in errors))
            self.assertTrue(any("'fuzzing' is 'FAIL'" in e for e in errors))

    def test_no_evidence_no_skeleton(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                rr.skeleton(pathlib.Path(d), "9.9.0")

    def test_the_newest_record_passes(self):
        newest = max((p for p in (ROOT / "docs/regulatory/releases").glob("*.md")
                      if p.stem[0].isdigit()), key=lambda p: tuple(int(x) for x in p.stem.split(".")))
        self.assertEqual(rr.check(ROOT, newest), [])


if __name__ == "__main__":
    unittest.main()
