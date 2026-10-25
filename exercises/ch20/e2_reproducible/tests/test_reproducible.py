# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 20.2: builds the variant's project twice, from two copies in
directories of different names, a clock second apart, and compares the programs.

    test_reproducible.py VARIANT_DIR [CXX]
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

VARIANT = pathlib.Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None
CXX = sys.argv.pop(1) if len(sys.argv) > 1 else "g++"


def build(src, where):
    shutil.copytree(src, where)
    env = {k: v for k, v in os.environ.items() if k != "SOURCE_DATE_EPOCH"}
    env["CXX"] = CXX
    for cmd in (["cmake", "-S", ".", "-B", "build", "-G", "Ninja", "-DCMAKE_BUILD_TYPE=RelWithDebInfo"],
                ["cmake", "--build", "build"]):
        p = subprocess.run(cmd, cwd=where, env=env, capture_output=True, text=True)
        if p.returncode != 0:
            raise AssertionError(f"{' '.join(cmd)} failed:\n{p.stdout}{p.stderr}")
    return where / "build" / "demo"


class Reproducible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.first = build(VARIANT, cls.tmp / "one" / "demo")
        start = int(time.time())
        while int(time.time()) == start:  # the second build in the next second of the clock
            time.sleep(0.05)  # sleep: poll
        cls.second = build(VARIANT, cls.tmp / "a-second" / "longer" / "checkout")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def output(self, program):
        return subprocess.run([str(program)], capture_output=True, text=True, check=True).stdout

    def test_the_program_still_says_what_it_is(self):
        self.assertIn("reproducible-demo 1.0", self.output(self.first))

    def test_the_log_names_its_source_relative_to_the_checkout(self):
        self.assertRegex(self.output(self.first), re.compile(r"^src/main\.cpp:\d+: starting$", re.M))

    def test_no_build_directory_is_in_the_program(self):
        data = self.first.read_bytes()
        self.assertNotIn(str(self.tmp).encode(), data)

    def test_the_program_keeps_its_debug_information(self):
        sections = subprocess.run(["readelf", "-S", "-W", str(self.first)], capture_output=True, text=True).stdout
        self.assertIn(".debug_info", sections)

    def test_two_builds_give_the_same_bytes(self):
        self.assertEqual(self.first.read_bytes(), self.second.read_bytes())


if __name__ == "__main__":
    unittest.main()
