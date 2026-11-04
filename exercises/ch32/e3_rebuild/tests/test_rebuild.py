# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 32.3: a change to config.hpp rebuilds what uses the configuration.

Builds the project with Ninja, touches a header, and asks Ninja which sources it would compile
(`ninja -n`, a dry run). Skipped with another generator, whose dry run lists no commands."""
import math
import os
import shutil
import subprocess
import unittest

from exproject import GENERATOR, PROJECT, build, configure, scratch

WANT = sum(4.0 * k + 2.0 * math.pi * 120.0 for k in range(8))


@unittest.skipUnless(GENERATOR == "Ninja", "the dry run needs Ninja")
class Rebuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = scratch("rebuild") / "rings"
        shutil.copytree(PROJECT, cls.src, ignore=shutil.ignore_patterns("build"))
        cls.build = cls.src / "build"
        r = configure(cls.src, cls.build)
        assert r.returncode == 0, r.output
        r = build(cls.build)
        assert r.returncode == 0, r.output

    def compiled_after_touching(self, header):
        os.utime(self.src / "src" / header)
        r = build(self.build, "--", "-n")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertEqual(build(self.build).returncode, 0)  # up to date again for the next test
        return sorted(line.rsplit("/", 1)[-1].removesuffix(".o")
                      for line in r.stdout.splitlines() if "Building CXX object" in line)

    def test_the_program_prints_the_sum_of_the_rings(self):
        out = subprocess.run([self.build / "rings"], capture_output=True, text=True, check=True)
        self.assertAlmostEqual(float(out.stdout), WANT, places=3)

    def test_touching_config_hpp_compiles_only_the_files_that_use_the_configuration(self):
        compiled = self.compiled_after_touching("config.hpp")
        self.assertEqual(compiled, ["config.cpp", "geometry.cpp", "main.cpp"])

    def test_the_rings_still_depend_on_the_geometry(self):
        compiled = self.compiled_after_touching("geometry.hpp")
        self.assertEqual(len([c for c in compiled if c.startswith("ring_")]), 8, compiled)


if __name__ == "__main__":
    unittest.main()
