#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_presets.py (Chapter 32)."""
import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_presets import check  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRESETS = json.loads((ROOT / "CMakePresets.json").read_text())
CI = "        preset: [debug, clang-release]\n"


class Presets(unittest.TestCase):
    def test_the_repository_presets_are_consistent(self):
        # REQ: SRS-BLD-002
        self.assertEqual(check(PRESETS, (ROOT / ".github/workflows/ci.yml").read_text()), [])

    def test_a_configuration_without_a_workflow_is_found(self):
        # REQ: SRS-BLD-002
        p = copy.deepcopy(PRESETS)
        p["workflowPresets"] = [w for w in p["workflowPresets"] if w["name"] != "tsan"]
        (e,) = check(p, CI)
        self.assertIn("tsan has no entry in workflowPresets", e)

    def test_a_workflow_that_skips_the_tests_is_found(self):
        # REQ: SRS-BLD-002
        p = copy.deepcopy(PRESETS)
        w = next(w for w in p["workflowPresets"] if w["name"] == "debug")
        w["steps"] = w["steps"][:2]
        (e,) = check(p, CI)
        self.assertIn("workflow debug", e)

    def test_a_test_preset_of_another_configuration_is_found(self):
        p = copy.deepcopy(PRESETS)
        next(t for t in p["testPresets"] if t["name"] == "debug")["configurePreset"] = "release"
        (e,) = check(p, CI)
        self.assertIn("test preset debug configures release", e)

    def test_a_ci_matrix_entry_without_a_preset_is_found(self):
        (e,) = check(PRESETS, "        preset: [debug, msan]\n")
        self.assertIn("msan", e)


if __name__ == "__main__":
    unittest.main()
