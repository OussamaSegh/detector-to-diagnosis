#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_format.py (Chapter 32), in a scratch git repository with the project's
.clang-format. Exit status 77 (CTest's skip) without clang-format and git-clang-format."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_format import check  # noqa: E402

ROOT = HERE.parent
# Formatted as the project's style wants it, and an old file that is not.
GOOD = "int add(int a, int b) { return a + b; }\n"
OLD_UNFORMATTED = "int   old( int a ){\nreturn a;}\n"


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=cwd, check=True, capture_output=True)


class CheckFormat(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.old_cwd = os.getcwd()
        shutil.copy(ROOT / ".clang-format", self.dir / ".clang-format")
        (self.dir / "a.cpp").write_text(GOOD)
        (self.dir / "old.cpp").write_text(OLD_UNFORMATTED)
        git("init", "-q", cwd=self.dir)
        git("add", ".", cwd=self.dir)
        git("commit", "-q", "-m", "base", cwd=self.dir)
        os.chdir(self.dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.dir)

    def stage(self, name, text):
        (self.dir / name).write_text(text)
        git("add", name, cwd=self.dir)

    def test_a_badly_formatted_staged_line_is_found(self):
        # REQ: SRS-BLD-004
        self.stage("a.cpp", GOOD + "int  sub(int a,int b){return a-b;}\n")
        ok, text = check(["--staged"])
        self.assertFalse(ok)
        self.assertIn("+int sub(int a, int b) { return a - b; }", text)

    def test_untouched_lines_of_an_unformatted_file_are_not_checked(self):
        # REQ: SRS-BLD-004
        self.stage("old.cpp", OLD_UNFORMATTED + "\nint added(int a) { return a; }\n")
        self.assertEqual(check(["--staged"])[0], True)

    def test_a_formatted_change_passes(self):
        # REQ: SRS-BLD-004
        self.stage("b.hpp", "#pragma once\n\nint twice(int a);\n")
        self.assertEqual(check(["--staged"]), (True, ""))

    def test_a_commit_range_is_checked(self):
        # REQ: SRS-BLD-004
        self.stage("a.cpp", GOOD + "int mul(int a,int b){return a*b;}\n")
        git("commit", "-q", "-m", "bad", cwd=self.dir)
        ok, _ = check(["HEAD~1", "HEAD"])
        self.assertFalse(ok)
        self.assertEqual(check(["HEAD~1", "HEAD~1"])[0], True)

    def test_files_that_are_not_cpp_are_not_checked(self):
        self.stage("notes.txt", "int  x(  ){}\n")
        self.assertEqual(check(["--staged"]), (True, ""))


if __name__ == "__main__":
    if shutil.which("clang-format") is None or shutil.which("git-clang-format") is None:
        print("clang-format or git-clang-format not installed: skipped")
        sys.exit(77)
    unittest.main()
