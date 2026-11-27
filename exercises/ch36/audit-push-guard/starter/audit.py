# SPDX-License-Identifier: MIT
"""Exercise 36.5 (A): your tests of the agent's push guard.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (push_guard.py). Write each
test from change/SPEC.md and from git's own documentation of push, not from the code.
"""
import unittest

OWN = "claude/feature-x"


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_push_of_the_sessions_branch_is_allowed(self):
        self.assertEqual(self.subject.refusals(f"git push -u origin {OWN}", OWN), [])

    # TODO: every way `git push` can force, delete or reach another branch (read the
    # <refspec> section of git help push).
