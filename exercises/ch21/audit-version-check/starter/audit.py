# SPDX-License-Identifier: MIT
"""Exercise 21.6 (A): your tests of the agent's version rules.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (version_rules.py). Write each
test from change/SPEC.md and from what a crash report needs, not from the code.
"""
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_dev_version_after_the_newest_release_is_right(self):
        self.assertEqual(self.subject.problems("0.4.0-dev", "Add the sorter", ["0.3.0"]), [])

    # TODO: every commit in the life of a release, from the last -dev commit to the first
    # commit after the tag, and every text a VERSION file might hold.
