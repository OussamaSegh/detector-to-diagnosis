#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of book/tools/xrefs.py (roadmap 2.0.0, Theme A)."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xrefs  # noqa: E402

CH = """# Two

See Chapter 1 and Exercise 2.1, Exercises 2.1 to 2.2, and Part I.

**Exercise 2.1 (E): One.** *Goal:* g. *Starter:* `exercises/ch02/e1_one/`. *Acceptance:* a.

**Exercise 2.2 (M, extra): Two.** *Goal:* g. *Starter:* `exercises/ch02/e2_two/`.
"""


def book(base, chapter=CH, solutions="## Exercise 2.1\n"):
    for d in ("book/src/part1", "book/solutions", "exercises/ch02/e1_one", "exercises/ch02/e2_two"):
        (base / d).mkdir(parents=True, exist_ok=True)
    (base / "book/src/part1/ch01-one.md").write_text("# One\n\nSee Chapter 2.\n")
    (base / "book/src/part1/ch02-two.md").write_text(chapter)
    (base / "book/solutions/ch02.md").write_text(solutions)


class Xrefs(unittest.TestCase):
    def check(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            book(pathlib.Path(d), **kw)
            return xrefs.check(pathlib.Path(d))

    def test_ranges_and_lists(self):
        self.assertEqual(xrefs.numbers("5.1 to 5.3"), ["5.1", "5.2", "5.3"])
        self.assertEqual(xrefs.numbers("18, 19 and 21"), ["18", "19", "21"])
        self.assertEqual(xrefs.numbers("3 to 5"), ["3", "4", "5"])

    def test_a_consistent_book_passes(self):
        self.assertEqual(self.check(), [])

    def test_each_kind_of_dangling_reference_is_found(self):
        errors = self.check(chapter=CH + "\nChapter 9, Exercise 2.7, Part IV.\n")
        text = "\n".join(errors)
        for want in ("Chapter 9 does not exist", "Exercise 2.7 is not defined", "Part IV does not exist"):
            self.assertIn(want, text)

    def test_a_reference_broken_across_lines_is_read_and_its_line_reported(self):
        # Review of 1.2.0: the check read line by line and missed "Chapter" + newline + "9".
        errors = self.check(chapter=CH + "\n```\ncode\n```\n\nSee Chapter\n9 and Exercise\n2.7.\n")
        self.assertIn("book/src/part1/ch02-two.md:13: Chapter 9 does not exist", errors)
        self.assertIn("book/src/part1/ch02-two.md:14: Exercise 2.7 is not defined", errors)

    def test_numbers_in_code_are_not_references(self):
        self.assertEqual(self.check(chapter=CH + "\n```\nChapter 9\n```\n\n`Exercise 9.9`\n"), [])

    def test_an_unknown_mark_and_a_wrong_starter(self):
        bad = CH.replace("(E)", "(S)").replace("ch02/e2_two", "ch02/e3_two")
        text = "\n".join(self.check(chapter=bad))
        self.assertIn("marked (S)", text)
        self.assertIn("starter is exercises/ch02/e3_two", text)

    def test_an_audit_is_marked_a_and_can_be_referred_to(self):
        # Roadmap 3.0.0, Theme Q: one audit exercise per Part, marked (A).
        audit = CH + "\n**Exercise 2.3 (A): Audit.** *Given:* `exercises/ch02/audit-x/change/`.\n"
        self.assertEqual(self.check(chapter=audit + "\nSee Exercise 2.3.\n"), [])
        self.assertIn("marked (A, extra)", "\n".join(self.check(chapter=audit.replace("(A)", "(A, extra)"))))

    def test_a_solution_under_the_wrong_chapter(self):
        self.assertTrue(self.check(solutions="## Exercise 1.1\n"))


if __name__ == "__main__":
    unittest.main()
