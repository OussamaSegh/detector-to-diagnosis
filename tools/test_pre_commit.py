#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/hooks/pre-commit (Chapter 32): commits in a scratch repository whose hooks are
this repository's. Exit status 77 (CTest's skip) without clang-format and git-clang-format."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Built at run time, so that this file does not itself add an address the hook refuses.
ADDRESS = "someone" + "@" + "company-name.ch"


class PreCommit(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(ROOT / ".clang-format", self.dir / ".clang-format")
        self.git("init", "-q")
        self.git("config", "core.hooksPath", str(ROOT / "tools/hooks"))
        self.git("add", ".clang-format")
        self.assertEqual(self.commit().returncode, 0)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                               *args], cwd=self.dir, capture_output=True, text=True)

    def commit(self):
        return self.git("commit", "-q", "-m", "change")

    def add(self, name, text):
        (self.dir / name).write_text(text)
        self.git("add", name)
        return self.commit()

    def test_a_clean_change_is_committed(self):
        # REQ: SRS-BLD-005
        r = self.add("a.cpp", "int add(int a, int b) { return a + b; }\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_an_address_is_refused_and_a_placeholder_is_not(self):
        # REQ: SRS-BLD-005
        r = self.add("notes.md", f"Contact: {ADDRESS}\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"adds the address {ADDRESS}", r.stdout + r.stderr)
        self.assertIn("privacy", r.stderr)
        r = self.add("notes.md", "Contact: someone@example.com, 1+me@users.noreply.github.com\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_decorator_or_an_annotation_is_not_an_address(self):
        r = self.add("t.py", "@unittest.skipUnless(True, 'x')\nclass A:\n    pass\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_unformatted_cpp_is_refused(self):
        # REQ: SRS-BLD-005
        r = self.add("a.cpp", "int  add(int a,int b){return a+b;}\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("format", r.stderr)

    def test_trailing_whitespace_is_refused(self):
        r = self.add("notes.md", "a line   \n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("whitespace", r.stderr)


if __name__ == "__main__":
    if shutil.which("clang-format") is None or shutil.which("git-clang-format") is None:
        print("clang-format or git-clang-format not installed: skipped")
        sys.exit(77)
    unittest.main()
