# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 36.3, with `git merge-file` as the oracle for clean merges."""
import os
import pathlib
import subprocess
import tempfile
import unittest

from merge3 import merge3

BASE = [f"line {n}\n" for n in range(1, 13)]


def edit(lines, **changes):
    """A copy of lines with line n replaced (n=text), removed (n=None) or text inserted
    before it (n=("insert", text))."""
    out = []
    for n, line in enumerate(lines, start=1):
        c = changes.get(f"l{n}", line)
        if isinstance(c, tuple):
            out += [c[1], line]
        elif c is not None:
            out.append(c)
    return out


def git_merge(base, ours, theirs):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, lines in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = pathlib.Path(d) / name
            p.write_text("".join(lines))
            paths.append(str(p))
        r = subprocess.run(["git", "merge-file", "-p", *paths], capture_output=True, text=True,
                           env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                                    GIT_CONFIG_NOSYSTEM="1"))
        return r.stdout, r.returncode


class Clean(unittest.TestCase):
    def check(self, ours, theirs):
        expected, conflicts = git_merge(BASE, ours, theirs)
        self.assertEqual(conflicts, 0)
        merged, n = merge3(BASE, ours, theirs)
        self.assertEqual(n, 0)
        self.assertEqual("".join(merged), expected)

    def test_changes_far_apart(self):
        self.check(edit(BASE, l2="two\n"), edit(BASE, l10="ten\n"))

    def test_an_insertion_and_a_deletion_shift_the_lines(self):
        self.check(edit(BASE, l3=("insert", "new before 3\n"), l4=("insert", "and 4\n")),
                   edit(BASE, l8=None, l11="eleven\n"))

    def test_the_same_change_on_both_sides(self):
        self.check(edit(BASE, l5="five\n", l9=None), edit(BASE, l5="five\n", l1="one\n"))

    def test_one_side_unchanged(self):
        self.check(BASE, edit(BASE, l6=None, l7=None, l12="twelve\n"))
        self.check(edit(BASE, l1=None), BASE)


class Conflicts(unittest.TestCase):
    def check(self, ours, theirs, conflicts):
        _, git_conflicts = git_merge(BASE, ours, theirs)
        merged, n = merge3(BASE, ours, theirs)
        self.assertEqual(n, conflicts)
        self.assertEqual(git_conflicts, conflicts)
        self.assertEqual(sum(line.startswith("<<<<<<< ") for line in merged), conflicts)
        self.assertEqual(sum(line == "=======\n" for line in merged), conflicts)
        return merged

    def test_two_changes_of_one_line(self):
        merged = self.check(edit(BASE, l4="four, ours\n"), edit(BASE, l4="four, theirs\n"), 1)
        at = merged.index("<<<<<<< ours\n")
        self.assertEqual(merged[at:at + 5], ["<<<<<<< ours\n", "four, ours\n", "=======\n",
                                             "four, theirs\n", ">>>>>>> theirs\n"])
        self.assertEqual(merged[:3], BASE[:3])
        self.assertEqual(merged[at + 5:], BASE[4:])

    def test_a_deletion_against_a_change(self):
        merged = self.check(edit(BASE, l7=None), edit(BASE, l7="seven\n"), 1)
        at = merged.index("<<<<<<< ours\n")
        self.assertEqual(merged[at + 1], "=======\n")

    def test_two_insertions_at_one_place(self):
        self.check(edit(BASE, l6=("insert", "ours\n")), edit(BASE, l6=("insert", "theirs\n")), 1)

    def test_a_conflict_and_a_clean_change_elsewhere(self):
        merged = self.check(edit(BASE, l2="two, ours\n", l11="eleven\n"),
                            edit(BASE, l2="two, theirs\n"), 1)
        self.assertIn("eleven\n", merged)

    def test_changes_of_two_adjacent_lines_conflict(self):
        self.check(edit(BASE, l4="four\n"), edit(BASE, l5="five\n"), 1)

    def test_two_conflicts(self):
        self.check(edit(BASE, l2="a\n", l10="b\n"), edit(BASE, l2="c\n", l10="d\n"), 2)


if __name__ == "__main__":
    unittest.main()
