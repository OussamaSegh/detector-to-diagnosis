# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 40.1."""
import unittest

from release import combined, kind, next_version


class Kind(unittest.TestCase):
    def test_a_fix_alone_is_a_patch(self):
        self.assertEqual(kind({"fixes_report": True}), "patch")
        self.assertEqual(kind({"soup_update": True}), "patch")
        self.assertEqual(kind({"documentation": True}), "patch")

    def test_a_fix_that_adds_or_changes_an_interface_is_not(self):
        # A fix that needs a new field in the run record is a minor release, one that renames a
        # field a major one: what the fix does decides, not why it was made.
        self.assertEqual(kind({"fixes_report": True, "changes_format": True}), "minor")
        self.assertEqual(kind({"fixes_report": True, "new_requirement": True}), "minor")
        self.assertEqual(kind({"fixes_report": True, "breaks_clients": True}), "major")
        self.assertEqual(kind({"soup_update": True, "new_soup": True}), "minor")

    def test_additions_are_minor_and_breaks_major(self):
        self.assertEqual(kind({"new_feature": True}), "minor")
        self.assertEqual(kind({"changes_api": True}), "minor")
        self.assertEqual(kind({"changes_api": True, "breaks_clients": True}), "major")

    def test_a_change_that_does_nothing_is_refused(self):
        with self.assertRaises(ValueError):
            kind({})


class Versions(unittest.TestCase):
    def test_a_release_takes_the_largest_kind_of_its_changes(self):
        self.assertEqual(combined([{"fixes_report": True}, {"new_feature": True},
                                   {"documentation": True}]), "minor")
        self.assertEqual(combined([{"documentation": True}, {"fixes_report": True}]), "patch")
        with self.assertRaises(ValueError):
            combined([])

    def test_the_lower_numbers_reset(self):
        self.assertEqual(next_version("1.3.0", "patch"), "1.3.1")
        self.assertEqual(next_version("1.3.2", "minor"), "1.4.0")
        self.assertEqual(next_version("1.3.2", "major"), "2.0.0")

    def test_only_a_released_version_has_a_next(self):
        for bad in ("2.0.0-dev", "1.3", "v1.3.0"):
            with self.assertRaises(ValueError, msg=bad):
                next_version(bad, "patch")
        with self.assertRaises(ValueError):
            next_version("1.3.0", "hotfix")


if __name__ == "__main__":
    unittest.main()
