# SPDX-License-Identifier: MIT
"""Exercise 31.5 (A): your tests of the agent's writable_out.

The acceptance runs this class against the corrected change and the agent's change;
self.subject is the module under audit (out_array.py). Write each test from change/SPEC.md and
from the arrays a scientist really has, not from the code.
"""
import unittest

import numpy as np


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_new_float64_array_of_the_right_shape_is_taken(self):
        out = np.zeros((4, 3))
        self.assertIs(self.subject.writable_out(out, (4, 3)), out)

    # TODO: where else do float64 arrays come from in a Python analysis (files, other
    # processes, other libraries), and which arrays must be refused?
