# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 32.4: a dependency pinned by the hash of its archive, and its
headers outside the project's warnings.

Writes tinylib-1.0.tar (and a tampered copy) with make_archive.py, then configures and builds
copies of the project in scratch directories. Nothing goes to the network."""
import shutil
import subprocess
import unittest

import make_archive
from exproject import PROJECT, build, configure, scratch


class Pin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = scratch("pin")
        cls.good = cls.work / "tinylib-1.0.tar"
        cls.bad = cls.work / "tampered" / "tinylib-1.0.tar"
        cls.bad.parent.mkdir()
        make_archive.write(cls.good)
        make_archive.write(cls.bad, tamper=True)

    def project(self, name):
        src = self.work / name
        shutil.copytree(PROJECT, src, ignore=shutil.ignore_patterns("build"))
        return src

    def test_the_program_builds_with_warnings_as_errors_and_runs(self):
        src = self.project("good")
        r = configure(src, src / "build", f"-DTINY_URL={self.good}")
        self.assertEqual(r.returncode, 0, r.output)
        r = build(src / "build")
        self.assertEqual(r.returncode, 0, r.output)
        out = subprocess.run([src / "build" / "usetiny"], capture_output=True, text=True,
                             check=True)
        self.assertEqual(out.stdout, "scaled 10\n")

    def test_a_replaced_archive_is_refused_at_configure(self):
        src = self.project("replaced")
        r = configure(src, src / "build", f"-DTINY_URL={self.bad}")
        self.assertNotEqual(r.returncode, 0, "the tampered archive was accepted")
        self.assertIn("does not match expected value", r.output)

    def test_the_project_s_own_code_still_fails_on_a_warning(self):
        src = self.project("own")
        with open(src / "main.cpp", "a") as f:
            f.write("\nint narrowed(double d) { return d; }\n")
        r = configure(src, src / "build", f"-DTINY_URL={self.good}")
        self.assertEqual(r.returncode, 0, r.output)
        r = build(src / "build")
        self.assertNotEqual(r.returncode, 0, "a narrowing in main.cpp built")
        self.assertIn("float-conversion", r.output)
        self.assertIn("narrowed", r.output)


if __name__ == "__main__":
    unittest.main()
