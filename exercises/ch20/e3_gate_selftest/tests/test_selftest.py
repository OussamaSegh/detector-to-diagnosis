# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 20.3. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import pathlib
import tempfile
import unittest

import gate
import mutants
import selftest as s


class TheRealGate(unittest.TestCase):
    def test_the_good_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gate.check(s.make_tree(pathlib.Path(tmp))), [])

    def test_there_are_at_least_four_faults(self):
        self.assertGreaterEqual(len(s.FAULTS), 4)

    def test_every_fault_is_caught_for_its_reason(self):
        self.assertEqual(set(s.run(gate.check).values()), {"caught"})


class Verdicts(unittest.TestCase):
    def test_each_verdict(self):
        self.assertEqual(s.verdict([], ["x.cpp:1: no SPDX"], r"no SPDX"), "caught")
        self.assertEqual(s.verdict([], [], r"no SPDX"), "NOT CAUGHT")
        self.assertEqual(s.verdict([], ["something else"], r"no SPDX"), "failed for another reason")
        self.assertEqual(s.verdict(["x"], ["x.cpp:1: no SPDX"], r"no SPDX"), "gate fails on correct code")


class BrokenGates(unittest.TestCase):
    """The self-test of the self-test: every broken gate must show up as not catching something."""

    def test_no_broken_gate_passes_the_self_test(self):
        for mutant in mutants.MUTANTS:
            with self.subTest(mutant=mutant.__name__):
                verdicts = s.run(mutant)
                self.assertNotEqual(set(verdicts.values()), {"caught"}, verdicts)


if __name__ == "__main__":
    unittest.main()
