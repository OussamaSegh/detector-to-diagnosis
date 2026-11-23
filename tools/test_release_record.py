#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/release_record.py (roadmap 2.0.0, Theme D)."""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import types
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

    def test_the_soak_row_names_the_length_the_release_checks_run(self):
        """MDQ-PR-087: the length is written in the script and in this table; they must agree."""
        script = (ROOT / "tools/release_checks.sh").read_text()
        minutes = re.search(r"tools/soak\.py .*--minutes (\d+)", script).group(1)
        soak = [name for name, keys, _ in rr.ROWS if name.startswith("soak")]
        self.assertEqual(soak, [f"soak, {minutes} minutes"])

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
            self.assertIn("| soak, 100 minutes | not run |", text)
            record = root / "docs/regulatory/releases/9.9.0.md"
            record.write_text(text)
            errors = rr.check(root, record)
            self.assertTrue(any("TODO(record)" in e for e in errors))
            self.assertTrue(any("'fuzzing' is 'FAIL'" in e for e in errors))

    def test_no_evidence_no_skeleton(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                rr.skeleton(pathlib.Path(d), "9.9.0")

    def test_the_newest_record_passes_the_rules_of_its_release(self):
        # A record is judged by the check of the commit it releases: a later change of the rules
        # (CR-0028 replaced the gcc-cxx23 rows with release) does not make an old record wrong.
        newest = max((p for p in (ROOT / "docs/regulatory/releases").glob("*.md")
                      if p.stem[0].isdigit()), key=lambda p: tuple(int(x) for x in p.stem.split(".")))
        text = newest.read_text()
        m = re.search(r"commit ([0-9a-f]{40})", text)
        self.assertIsNotNone(m, f"{newest.name} names no commit")
        rules = subprocess.run(["git", "-C", str(ROOT), "show",
                                f"{m.group(1)}:exercises/ch14/e5_release_check/solution/release_check.py"],
                               capture_output=True, text=True, check=False)
        if rules.returncode != 0:
            self.skipTest("no git history to read the rules of the release from")
        module = types.ModuleType("release_check_at_release")
        exec(compile(rules.stdout, "release_check.py", "exec"), module.__dict__)
        errors = module.check(text, ROOT / "docs/regulatory")
        errors += [line for line in text.splitlines() if rr.TODO in line]
        self.assertEqual(errors, [])

    def test_a_table_row_that_differs_from_the_evidence_is_refused(self):
        """MDQ-PR-089: the 2.1.0 record's table said 30 minutes next to a soak of 100."""
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            ev = root / "measurements/release-9.9.0"
            ev.mkdir(parents=True)
            (ev / "commit.txt").write_text("commit " + "a" * 40 + "\n")
            (ev / "release-checks.txt").write_text(CHECKS + "pass  soak, 100 minutes at 1 M singles/s\n")
            record = root / "9.9.0.md"
            rows = rr.table_rows(root, "9.9.0")
            self.assertIn("| soak, 100 minutes | pass | `../../measurements/release-9.9.0/soak.txt` |", rows)
            self.assertEqual(rr.table_drift(root, record, "\n".join(rows)), [])
            stale = "\n".join(rows).replace("soak, 100 minutes", "soak, 30 minutes")
            self.assertEqual(len(rr.table_drift(root, record, stale)), 1)
            wrong = "\n".join(rows).replace("| fuzzing | FAIL |", "| fuzzing | pass |")
            self.assertEqual(len(rr.table_drift(root, record, wrong)), 1)

    def test_the_newest_record_has_every_row_its_evidence_gives(self):
        newest = max((p for p in (ROOT / "docs/regulatory/releases").glob("*.md")
                      if p.stem[0].isdigit()), key=lambda p: tuple(int(x) for x in p.stem.split(".")))
        self.assertEqual(rr.table_drift(ROOT, newest, newest.read_text()), [])

    def test_the_current_rules_ask_for_the_current_presets(self):
        spec = rr.exercise_check(ROOT).__globals__
        for p in rr.PRESETS:
            self.assertIn(f"build {p}", spec["REQUIRED_CHECKS"])
            self.assertIn(f"tests {p}", spec["REQUIRED_CHECKS"])

if __name__ == "__main__":
    unittest.main()
