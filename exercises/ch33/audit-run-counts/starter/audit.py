# SPDX-License-Identifier: MIT
"""Exercise 33.5 (A): your tests of the agent's count checks.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (run_counts.py). Write each
test from change/SPEC.md and from the sorter's report as Chapter 10 and this chapter define
it, not from the code.
"""
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_partition_that_adds_up_has_no_problem(self):
        c = {"singles_in": 10, "energy_rejected": 2, "alone": 2, "pairs": 3, "in_multiples": 0,
             "out_of_order": 0}
        self.assertEqual(self.subject.partition_problems(c), [])

    # TODO: every counter of the report, each off by one; and where exactly a run ends.
