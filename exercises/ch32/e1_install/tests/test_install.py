# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 32.1: pulse as an installable CMake package."""
import pathlib
import shutil
import subprocess
import unittest

from exproject import HERE, PROJECT, build, cmake, configure, scratch


def install(work):
    """Builds the project and installs it under work/prefix; returns the prefix."""
    b, prefix = work / "build", work / "prefix"
    r = configure(PROJECT, b)
    assert r.returncode == 0, r.output
    r = build(b)
    assert r.returncode == 0, r.output
    r = cmake("--install", b, "--prefix", prefix)
    assert r.returncode == 0, r.output
    return prefix


class Install(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = scratch("install")
        cls.prefix = install(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def consumer(self, prefix, version="1.2"):
        b = scratch("consumer")
        r = configure(HERE / "consumer", b, f"-DCMAKE_PREFIX_PATH={prefix}",
                      f"-DPULSE_VERSION={version}")
        return b, r

    def test_installs_a_package_configuration_version_and_targets_file(self):
        names = {p.name for p in self.prefix.rglob("*.cmake")}
        for f in ("pulseConfig.cmake", "pulseConfigVersion.cmake", "pulseTargets.cmake"):
            self.assertIn(f, names, f"{f} is not installed")

    def test_no_installed_cmake_file_names_a_path_of_this_machine(self):
        for p in self.prefix.rglob("*.cmake"):
            text = p.read_text()
            for d in (PROJECT, self.work / "build"):
                self.assertNotIn(str(d), text, f"{p.name} names {d}")

    def test_a_moved_installation_is_found_built_against_and_run(self):
        moved = scratch("moved") / "elsewhere"
        shutil.copytree(self.prefix, moved, symlinks=True)
        b, r = self.consumer(moved)
        self.assertEqual(r.returncode, 0, r.output)
        r = build(b)
        self.assertEqual(r.returncode, 0, r.output)
        out = subprocess.run([b / "consumer"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(out.stdout.strip(), "area 70 peak 2")

    def test_an_older_minor_version_is_accepted_and_a_newer_major_refused(self):
        self.assertEqual(self.consumer(self.prefix, "1.0")[1].returncode, 0)
        _, r = self.consumer(self.prefix, "2.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("1.2.0", r.output)


if __name__ == "__main__":
    unittest.main()
