# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 21.1. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this).

The review of tests/change.diff is graded against the defects seeded in it. A finding matches a
seeded defect when it has the defect's category and points at one of its lines (lines of
change.diff, counted from 1). The seeded defects are listed here, so read the diff first."""
import pathlib
import unittest

from findings import FINDINGS

DIFF = pathlib.Path(__file__).resolve().parent / "change.diff"
SEVERITIES = ("blocker", "major", "minor", "question")
CATEGORIES = ("correctness", "concurrency", "lifetime", "error-path", "input", "tests")

# name: (category, lines of change.diff, a blocker?)
SEEDED = {
    "the receive thread and the control thread share counts_ without synchronization":
        ("concurrency", range(59, 72), True),
    "rate() reads one slot past the window (and past the array), and not the last seconds":
        ("correctness", range(69, 74), True),
    "label() returns a view of a string that ends with the function":
        ("lifetime", range(76, 80), True),
    "set_window() changes the window before it rejects the value; a window of 0 divides by 0":
        ("error-path", list(range(82, 87)) + [73], False),
    "the first add() after a long pause (or with real time) clears seconds for ever":
        ("correctness", range(59, 62), False),
    "the test sleeps, checks only rate() > 0, and names no requirement":
        ("tests", range(104, 114), False),
}


def matches(finding, category, lines):
    return finding.get("category") == category and finding.get("line") in lines


class Review(unittest.TestCase):
    def test_every_finding_is_well_formed(self):
        n = len(DIFF.read_text().splitlines())
        for f in FINDINGS:
            self.assertIn(f.get("severity"), SEVERITIES, f)
            self.assertIn(f.get("category"), CATEGORIES, f)
            self.assertIsInstance(f.get("line"), int, f)
            self.assertTrue(1 <= f["line"] <= n, f)
            self.assertGreater(len(str(f.get("text", "")).split()), 5, f"say what and why: {f}")

    def test_every_blocker_is_found_and_not_called_minor(self):
        for name, (category, lines, blocker) in SEEDED.items():
            if not blocker:
                continue
            found = [f for f in FINDINGS if matches(f, category, lines)]
            self.assertTrue(found, f"not found: {name}")
            self.assertTrue(any(f["severity"] in ("blocker", "major") for f in found),
                            f"found, but not as a blocker or major finding: {name}")

    def test_at_least_five_of_the_six_are_found(self):
        missed = [name for name, (category, lines, _) in SEEDED.items()
                  if not any(matches(f, category, lines) for f in FINDINGS)]
        self.assertLessEqual(len(missed), 1, f"missed: {missed}")

    def test_few_findings_that_are_not_there(self):
        # A minor finding or a question costs nothing; a blocker or major finding that points at
        # no seeded defect costs the author time. Two are allowed: the diff has more to say.
        false = [f for f in FINDINGS if f.get("severity") in ("blocker", "major")
                 and not any(matches(f, c, lines) for c, lines, _ in SEEDED.values())]
        self.assertLessEqual(len(false), 2, f"blocker or major findings with no seeded defect: {false}")


if __name__ == "__main__":
    unittest.main()
