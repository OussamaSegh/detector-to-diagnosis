#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/audit_exercises.py (TL-70): the patch it applies, and each way a record of an
audit exercise can be incomplete or untrue."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_exercises as ae  # noqa: E402

BEFORE = "a = 1\nb = 2\nc = 3\n"
AGENT = "a = 1\nb = 20\nc = 3\nd = 4\n"
PATCH = """--- a/m.py
+++ b/m.py
@@ -1,3 +1,4 @@
 a = 1
-b = 2
+b = 20
 c = 3
+d = 4
"""


def make_repo(root):
    (root / "docs/regulatory").mkdir(parents=True)
    (root / "docs/regulatory/problem-reports.json").write_text(
        json.dumps({"reports": [{"id": "MDQ-PR-001"}]}))
    (root / "book/src/part1").mkdir(parents=True)
    (root / "book/src/part1/ch01-x.md").write_text(
        "## Exercises\n\n**Exercise 1.9 (A): An audit.** *Given:*\n"
        "`exercises/ch01/audit-x/change/`.\n")
    d = root / "exercises/ch01/audit-x"
    for sub in ("change/before", "tests/agent", "tests/reference", "starter", "solution"):
        (d / sub).mkdir(parents=True)
    (d / "README.md").write_text("# Exercise 1.9 (A)\n")
    (d / "change/SPEC.md").write_text("spec\n")
    (d / "change/TRANSCRIPT.md").write_text("session\n")
    (d / "change/agent.patch").write_text(PATCH)
    (d / "change/before/m.py").write_text(BEFORE)
    (d / "tests/agent/m.py").write_text(AGENT)
    (d / "tests/reference/m.py").write_text(AGENT)
    (d / "solution/REPORT.md").write_text("Defect: MDQ-PR-001.\n")
    return d


class Patch(unittest.TestCase):
    def test_a_patch_applies_with_its_context(self):
        [(path, hunks)] = ae.parse_patch(PATCH)
        self.assertEqual(path, "m.py")
        self.assertEqual(ae.apply(BEFORE, hunks), AGENT)

    def test_a_patch_whose_context_differs_does_not_apply(self):
        [(_, hunks)] = ae.parse_patch(PATCH)
        with self.assertRaises(ae.PatchError):
            ae.apply("a = 1\nb = 3\nc = 3\n", hunks)

    def test_a_truncated_hunk_is_an_error(self):
        with self.assertRaises(ae.PatchError):
            ae.parse_patch(PATCH.rsplit("\n", 3)[0] + "\n")

    def test_a_new_file_applies_to_nothing(self):
        [(_, hunks)] = ae.parse_patch("--- /dev/null\n+++ b/n.py\n@@ -0,0 +1,2 @@\n+x\n+y\n")
        self.assertEqual(ae.apply("", hunks), "x\ny\n")


class Record(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.d = make_repo(self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def errors(self):
        return ae.check(self.root, self.d)

    def test_a_complete_record_passes(self):
        self.assertEqual(self.errors(), [])

    def test_a_missing_part_is_named(self):
        (self.d / "change/TRANSCRIPT.md").unlink()
        self.assertIn("change/TRANSCRIPT.md is missing", "\n".join(self.errors()))

    def test_code_that_is_not_the_patch_applied_is_reported(self):
        (self.d / "tests/agent/m.py").write_text(AGENT + "e = 5\n")
        self.assertIn("is not tests/agent/m.py", "\n".join(self.errors()))

    def test_a_patch_that_does_not_apply_is_reported(self):
        (self.d / "change/before/m.py").write_text("a = 1\n")
        self.assertIn("does not apply", "\n".join(self.errors()))

    def test_a_report_without_a_problem_report_is_reported(self):
        (self.d / "solution/REPORT.md").write_text("Defect: invented.\n")
        self.assertIn("names no problem report", "\n".join(self.errors()))

    def test_an_unknown_problem_report_is_reported(self):
        (self.d / "solution/REPORT.md").write_text("MDQ-PR-001 and MDQ-PR-999.\n")
        self.assertIn("MDQ-PR-999, which is not a problem report", "\n".join(self.errors()))

    def test_an_exercise_the_chapter_does_not_mark_a_is_reported(self):
        ch = self.root / "book/src/part1/ch01-x.md"
        ch.write_text(ch.read_text().replace("(A)", "(M)"))
        self.assertIn("no exercise marked (A)", "\n".join(self.errors()))

    def test_the_command_fails_on_a_bad_record(self):
        (self.d / "change/SPEC.md").unlink()
        p = subprocess.run([sys.executable, str(HERE / "audit_exercises.py"), str(self.root)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)


class Repository(unittest.TestCase):
    def test_every_audit_exercise_of_the_book_has_a_complete_record(self):
        root = HERE.parent
        dirs = sorted(root.glob("exercises/ch*/audit-*"))
        self.assertEqual(len(dirs), 10, "Theme Q: one audit exercise per Part I to X")
        self.assertEqual([e for d in dirs for e in ae.check(root, d)], [])


if __name__ == "__main__":
    unittest.main()
