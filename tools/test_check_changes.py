#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_changes.py's list of test names: a change request may name a test of
any place the project keeps tests, the book's build tools included (CR-0039)."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_changes  # noqa: E402


class Tests(unittest.TestCase):
    def test_every_place_that_holds_tests_is_read(self):
        names = check_changes.tests(ROOT)
        for name in ("Photos.test_a_photo_without_a_credit_fails",     # book/tools
                     "Recorded.test_the_rerun_of_2_2_0_fails_acc_04_but_not_acc_10",  # tools
                     "Verdicts.test_the_candidate_is_compared_with_the_previous_release"):
            self.assertIn(name, names)
        self.assertNotIn("Photos.test_that_does_not_exist", names)


if __name__ == "__main__":
    unittest.main()
