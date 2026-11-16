# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 40.3.

A small history with the shapes that matter: the defect comes in with x on a feature branch,
merged into main at M (x is reachable from M only through its second parent); the fix is f on
main; release/1.3 branches at M, and p1 there is a cherry-pick of f; s2 on another branch is a
cherry-pick of p1; release/1.2 branches at c, before the merge. Commit ids are names here; in
git they are hashes.
"""
import unittest

from affected import affected


def history():
    def c(parents, message=""):
        return {"parents": parents, "message": message}

    return {
        "a": c([]),
        "b": c(["a"]),
        "x": c(["b"], "Add the passphrase to the key loader"),       # introduces the defect
        "i": c(["b"]),
        "c": c(["i"]),
        "y": c(["x"]),
        "M": c(["c", "y"], "Merge branch 'feature'"),
        "f": c(["M"], "Ask for no passphrase on the terminal (MDQ-PR-073)"),   # the fix
        "d": c(["f"]),
        "e": c(["d"]),
        "g": c(["e"]),
        # release/1.3 starts at M: 1.3.0 had the defect
        "r1": c(["M"]),
        "p1": c(["r1"], "Ask for no passphrase on the terminal (MDQ-PR-073)\n\n"
                        "(cherry picked from commit f)"),
        "r2": c(["p1"]),
        # release/1.2 starts at c, before the merge: it never had the defect
        "q1": c(["c"]),
        # a pick of the pick, onto a branch from M
        "s1": c(["M"]),
        "s2": c(["s1"], "Ask for no passphrase (MDQ-PR-073)\n\n(cherry picked from commit p1)"),
    }


TAGS = {"1.2.0": "c", "1.2.1": "q1", "1.3.0": "M", "1.3.1": "r1", "1.3.2": "r2",
        "2.0.0": "e", "2.1.0": "g", "1.10.0": "s1", "1.10.1": "s2"}


class Affected(unittest.TestCase):
    def test_a_defect_merged_from_a_branch_is_found(self):
        got = affected(history(), TAGS, "x", "f")
        self.assertIn("1.3.0", got)          # x reaches M through its second parent

    def test_a_cherry_picked_fix_counts_as_the_fix(self):
        got = affected(history(), TAGS, "x", "f")
        self.assertIn("1.3.1", got)          # r1 is before the pick
        self.assertNotIn("1.3.2", got)       # r2 has p1, the pick of f
        self.assertNotIn("1.10.1", got)      # s2 has the pick of the pick

    def test_the_whole_answer_in_version_order(self):
        self.assertEqual(affected(history(), TAGS, "x", "f"), ["1.3.0", "1.3.1", "1.10.0"])

    def test_a_release_before_the_defect_is_not_affected(self):
        got = affected(history(), TAGS, "x", "f")
        self.assertNotIn("1.2.0", got)
        self.assertNotIn("1.2.1", got)

    def test_a_defect_fixed_before_any_release_affects_none(self):
        h = history()
        tags = {"2.0.0": "e", "2.1.0": "g"}
        self.assertEqual(affected(h, tags, "x", "f"), [])

    def test_a_long_history_does_not_overflow(self):
        commits = {"0": {"parents": [], "message": ""}}
        for k in range(1, 20000):
            commits[str(k)] = {"parents": [str(k - 1)], "message": ""}
        self.assertEqual(affected(commits, {"9.0.0": "19999"}, "5", "19999"), [])
        self.assertEqual(affected(commits, {"9.0.0": "19998"}, "5", "19999"), ["9.0.0"])


if __name__ == "__main__":
    unittest.main()
