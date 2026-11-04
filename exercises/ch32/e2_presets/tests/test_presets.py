# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 32.2: CMakePresets.json with a workflow per configuration.

Each test copies the project to a scratch directory and runs `cmake --workflow --preset NAME`
there, with this build's compiler and generator in the environment (CXX, CMAKE_GENERATOR), as
a developer's shell or a CI job would have them."""
import os
import shutil
import subprocess
import unittest

from exproject import CMAKE, CXX, GENERATOR, PROJECT, scratch


class Presets(unittest.TestCase):
    def workflow(self, name):
        src = scratch(name) / "window"
        shutil.copytree(PROJECT, src, ignore=shutil.ignore_patterns("build"))
        env = dict(os.environ, CXX=CXX, CMAKE_GENERATOR=GENERATOR)
        r = subprocess.run([CMAKE, "--workflow", "--preset", name], cwd=src, env=env,
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_the_dev_workflow_configures_builds_and_passes_the_tests(self):
        rc, out = self.workflow("dev")
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("100% tests passed, 0 tests failed out of 2", out)

    def test_the_asan_workflow_finds_the_read_past_the_array(self):
        rc, out = self.workflow("asan")
        self.assertNotEqual(rc, 0, out[-3000:])
        # It fails in the test step, for the defect, not in the build.
        self.assertIn("ERROR: AddressSanitizer: heap-buffer-overflow", out, out[-3000:])
        self.assertIn("window.cpp", out)

    def test_each_configuration_has_a_build_test_and_workflow_preset(self):
        r = subprocess.run([CMAKE, "--list-presets=all"], cwd=PROJECT, capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for kind in ("Available configure presets", "Available build presets",
                     "Available test presets", "Available workflow presets"):
            section = r.stdout.split(kind, 1)
            self.assertEqual(len(section), 2, f"no {kind.split()[1]} presets")
            block = section[1].split("Available", 1)[0]
            for name in ("dev", "asan"):
                self.assertIn(f'"{name}"', block, f"no {name} in {kind.split()[1]} presets")


if __name__ == "__main__":
    unittest.main()
