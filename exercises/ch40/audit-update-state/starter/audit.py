# SPDX-License-Identifier: MIT
"""Exercise 40.5 (A): your tests of the agent's open_state.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (update_state.py). Write each
test from change/SPEC.md and from what a field engineer can do with the answer.
"""
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_store_with_a_trial_is_read(self):
        s = self.subject.open_state('{"good": "a", "good_version": "2.3.0", "trial": "b", '
                                    '"trial_version": "3.0.0"}')
        self.assertEqual((s.good, s.trial, s.trial_version), ("a", "b", "3.0.0"))

    # TODO: a state.json a person edited by hand, or a disk damaged, can hold any JSON in
    # any field.
