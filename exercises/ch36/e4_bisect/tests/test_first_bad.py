# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 36.4, on histories of named commits with a known first bad one."""
import math
import unittest

import first_bad as b


def history(n):
    return [f"c{k:03d}" for k in range(n)]


def oracle(commits, first_bad, untestable=()):
    """A test that fails from first_bad on and cannot run on the untestable commits; it records
    every commit it is asked about."""
    asked = []
    where = {c: i for i, c in enumerate(commits)}

    def test(c):
        asked.append(c)
        if c in untestable:
            return "skip"
        return "bad" if where[c] >= where[first_bad] else "good"

    return test, asked


class Bisect(unittest.TestCase):
    def test_without_skips_it_finds_the_commit_in_log2_tests(self):
        commits = history(100)
        for first in ("c001", "c037", "c098", "c099"):
            test, asked = oracle(commits, first)
            found, candidates, tested = b.bisect(commits, "c000", "c099", test)
            self.assertEqual((found, candidates), (first, [first]), first)
            self.assertEqual(tested, asked)
            self.assertLessEqual(len(tested), math.ceil(math.log2(99)), first)

    def test_an_untestable_commit_elsewhere_changes_nothing(self):
        commits = history(100)
        test, asked = oracle(commits, "c037", untestable={"c049", "c050", "c051"})
        found, candidates, _ = b.bisect(commits, "c000", "c099", test)
        self.assertEqual((found, candidates), ("c037", ["c037"]))

    def test_an_untestable_commit_just_before_leaves_both_open(self):
        commits = history(100)
        test, _ = oracle(commits, "c038", untestable={"c037"})
        found, candidates, _ = b.bisect(commits, "c000", "c099", test)
        self.assertIsNone(found)
        self.assertEqual(candidates, ["c037", "c038"])

    def test_a_run_of_untestable_commits_is_reported_whole(self):
        commits = history(60)
        broken = {f"c{k:03d}" for k in range(20, 26)}  # a build broken for six commits
        test, _ = oracle(commits, "c023", untestable=broken)
        found, candidates, tested = b.bisect(commits, "c000", "c059", test)
        self.assertIsNone(found)
        self.assertEqual(candidates, [f"c{k:03d}" for k in range(20, 27)])
        self.assertEqual(len(tested), len(set(tested)), "a commit was tested twice")

    def test_only_commits_between_good_and_bad_are_tested(self):
        commits = history(50)
        test, asked = oracle(commits, "c030")
        b.bisect(commits, "c010", "c040", test)
        self.assertTrue(all("c010" < c < "c040" for c in asked), asked)

    def test_adjacent_good_and_bad_need_no_test(self):
        commits = history(10)
        test, asked = oracle(commits, "c005")
        self.assertEqual(b.bisect(commits, "c004", "c005", test), ("c005", ["c005"], []))

    def test_impossible_starts_and_answers_are_refused(self):
        commits = history(10)
        test, _ = oracle(commits, "c005")
        for good, bad in (("c007", "c003"), ("c004", "c004"), ("x", "c009")):
            with self.assertRaises(ValueError):
                b.bisect(commits, good, bad, test)
        with self.assertRaises(ValueError):
            b.bisect(commits, "c000", "c009", lambda c: "flaky")


if __name__ == "__main__":
    unittest.main()
