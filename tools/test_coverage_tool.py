#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/coverage.py's list of gaps per file (roadmap 2.2.0, Theme R)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coverage as cov  # noqa: E402

ROOT = pathlib.Path("/src")
SHOWN = """/src/a.cpp:
    1|      1|int f(bool x) {
    2|      1|  if (x) {
  ------------------
  |  Branch (2:7): [True: 1, False: 0]
  ------------------
    3|      1|    return 1;
/src/b.cpp:
    1|      2|int g(bool y) {
    2|      2|  if (y) {
  ------------------
  |  Branch (2:7): [True: 1, False: 1]
  ------------------
"""


class UncoveredByFile(unittest.TestCase):
    def test_each_file_has_its_heading_and_its_own_gaps(self):
        text = cov.uncovered_by_file(SHOWN, ["/src/a.cpp", "/src/b.cpp"], ROOT)
        a, b = text.split("## b.cpp")
        self.assertIn("## a.cpp", a)
        self.assertIn("2: if (x) {", a)
        self.assertIn("column 7: branch never false", a)
        self.assertEqual(b.strip(), "none")

    def test_a_file_the_output_lacks_is_listed_as_none(self):
        text = cov.uncovered_by_file(SHOWN, ["/src/a.cpp", "/src/c.cpp"], ROOT)
        self.assertIn("## c.cpp\nnone", text)
        self.assertNotIn("b.cpp", text)


if __name__ == "__main__":
    unittest.main()
