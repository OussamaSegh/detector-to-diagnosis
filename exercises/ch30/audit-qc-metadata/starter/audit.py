# SPDX-License-Identifier: MIT
"""Exercise 30.5 (A): your tests of the agent's read_metadata.

The acceptance runs this class against the corrected change, the agent's change and each of
its defects on its own; self.subject is the module under audit (qc_metadata.py). Write each
test from change/SPEC.md and from what a technologist can do with the answer.
"""
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_reads_a_complete_run(self):
        m = self.subject.read_metadata({"scanner": {"crystals": 1024},
                                        "records": {"delayed_window_ps": 80_000}})
        self.assertEqual((m.crystals, m.delayed_window_ps), (1024, 80_000))

    # TODO: everything a JSON file can hold where the report expects an integer or an object.
