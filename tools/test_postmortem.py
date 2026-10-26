#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/core_build_id.py and tools/postmortem.sh (Chapter 21).

Usage: test_postmortem.py SERVER OTHER_PROGRAM. The core dump is made by gdb
(generate-core-file) from SERVER stopped at its first instruction, so the test needs neither a
crash nor the system's core dump settings. Exit status 77 (skipped) without gdb and readelf.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from core_build_id import Core, build_id  # noqa: E402

SERVER = OTHER = None


def readelf_build_id(path):
    out = subprocess.run(["readelf", "-n", str(path)], capture_output=True, text=True).stdout
    m = re.search(r"Build ID: ([0-9a-f]+)", out)
    return m.group(1) if m else None


def postmortem(*args):
    r = subprocess.run([str(TOOLS / "postmortem.sh"), *map(str, args)], capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


class Postmortem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="minidaq-postmortem-"))
        cls.core = cls.tmp / "server.core"
        subprocess.run(["gdb", "-batch", "-nx", "-iex", "set debuginfod enabled off", "-ex", "starti",
                        "-ex", f"generate-core-file {cls.core}", "--args", SERVER, "--port", "0"],
                       capture_output=True, timeout=120, check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_the_build_id_in_the_core_is_the_programs(self):
        _, bid = build_id(Core(self.core), pathlib.Path(SERVER).name)
        self.assertEqual(bid, readelf_build_id(SERVER))
        self.assertEqual(build_id(Core(self.core))[1], bid, "without a name: the first file mapped")

    def test_a_matching_program_gives_the_stacks(self):
        code, out = postmortem(self.core, SERVER)
        self.assertEqual(code, 0, out)
        self.assertIn("build ID in the core:       " + readelf_build_id(SERVER), out)
        self.assertIn("== crashing thread", out)
        self.assertRegex(out, r"#0 ")

    def test_another_build_of_the_same_name_is_refused(self):
        # The everyday mistake: the program of the same name from another build.
        impostor = self.tmp / "other" / pathlib.Path(SERVER).name
        impostor.parent.mkdir(exist_ok=True)
        shutil.copy(OTHER, impostor)
        code, out = postmortem(self.core, impostor)
        self.assertEqual(code, 2, out)
        self.assertIn("is not the program of", out)

    def test_a_debug_file_of_another_build_is_refused(self):
        debug = self.tmp / "other.debug"
        subprocess.run(["objcopy", "--only-keep-debug", OTHER, str(debug)], check=True)
        code, out = postmortem(self.core, SERVER, debug)
        self.assertEqual(code, 2, out)
        self.assertIn("the debug information of another build", out)

    def test_a_file_that_is_not_a_core_is_refused(self):
        code, out = postmortem(SERVER, SERVER)
        self.assertEqual(code, 2, out)
        self.assertIn("not a core dump", out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: test_postmortem.py SERVER OTHER_PROGRAM")
    if not (shutil.which("gdb") and shutil.which("readelf") and shutil.which("objcopy")):
        print("gdb, readelf or objcopy not installed: skipped")
        sys.exit(77)
    SERVER, OTHER = sys.argv[1], sys.argv[2]
    unittest.main(argv=sys.argv[:1])
