#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_version.py (Chapter 21)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_version import problems  # noqa: E402

RELEASED = ["0.1.0", "0.2.0", "0.3.0"]


class Version(unittest.TestCase):
    def test_a_dev_version_after_the_newest_release_passes(self):
        self.assertEqual(problems("0.4.0-dev", "ch21: diagnostics", RELEASED, False), [])

    def test_a_release_version_after_its_release_commit_fails(self):
        # MDQ-PR-024: every commit of Part IV said 0.3.0.
        (p,) = problems("0.3.0", "ch20: CI for a regulated project", RELEASED, False)
        self.assertIn("not its release commit", p)

    def test_the_release_commit_and_its_preparation_pass(self):
        self.assertEqual(problems("0.4.0", "Release 0.4.0: Part IV complete", RELEASED, False), [])
        self.assertEqual(problems("0.4.0", "ch21: diagnostics", RELEASED, True), [])

    def test_a_dev_version_of_a_released_version_fails(self):
        (p,) = problems("0.3.0-dev", "ch16: QMS", RELEASED, False)
        self.assertIn("not later than the newest release, 0.3.0", p)

    def test_versions_compare_as_numbers(self):
        self.assertEqual(problems("0.10.0-dev", "x", ["0.9.0"], False), [])

    def test_anything_else_is_not_a_version(self):
        for bad in ("0.4", "v0.4.0", "0.4.0-rc1", ""):
            self.assertEqual(len(problems(bad, "x", RELEASED, False)), 1, bad)

    def test_outside_git_only_the_order_is_checked(self):
        self.assertEqual(problems("0.3.0", None, RELEASED, False), [])


if __name__ == "__main__":
    unittest.main()
