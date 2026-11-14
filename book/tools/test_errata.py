#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of book/tools/errata.py (roadmap 2.0.0, Theme A)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import errata  # noqa: E402

V = {"1.0.0", "1.1.0"}


def e(n, found=("1.0.0",), fixed="1.1.0", **kw):
    d = {"id": f"E-{n:03d}", "where": "Chapter 1", "found_in": list(found), "fixed_in": fixed, "text": "t"}
    d.update(kw)
    return d


class Errata(unittest.TestCase):
    def test_a_consistent_list_passes(self):
        self.assertEqual(errata.check([e(1), e(2, fixed=None), e(3, fixed="1.2.0")], V), [])

    def test_each_mistake_is_found(self):
        cases = [
            ([e(2)], "expected id E-001"),
            ([e(1, found=("0.9.9",))], "never released"),
            ([e(1, fixed="1.0.5")], "never released and is not a coming version"),
            ([e(1, found=("1.1.0",), fixed="1.1.0")], "not later than every version"),
            ([e(1, text="")], "missing text"),
            ([e(1, fixed="next")], "not X.Y.Z"),
        ]
        for items, want in cases:
            self.assertIn(want, "\n".join(errata.check(items, V)), want)

    def test_the_page_lists_newest_first_and_escapes(self):
        text = errata.page([e(1, text="a < b"), e(2, fixed=None)], "1.2.0", "https://x")
        self.assertLess(text.index("E-002"), text.index("E-001"))
        self.assertIn("a &lt; b", text)
        self.assertIn("open.", text)

    def test_the_repository_errata(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        self.assertEqual(errata.main(["x", "check", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
