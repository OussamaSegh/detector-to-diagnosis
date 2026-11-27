# SPDX-License-Identifier: MIT
"""Exercise 8.6 (A): your tests of the agent's find_pairs.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (pairs.py). Write each test
from the specification in change/SPEC.md and the physics of this chapter, not from the code.
"""
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_two_singles_in_one_window_are_one_pair(self):
        S = self.subject.Single
        a, b = S(0, 1, 511.0), S(1_000, 2, 511.0)
        self.assertEqual(len(self.subject.find_pairs([a, b], 4_000)), 1)

    # TODO: what does the specification promise that this test does not check? Think of how
    # many pairs a stream of well separated annihilations gives, of the randoms rate of two
    # independent detectors (Exercise 8.3), and of singles that arrive in another order.
