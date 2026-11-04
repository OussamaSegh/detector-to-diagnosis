# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 34.1."""
import unittest

from coupling import coupling


def log(*commits):
    return "".join(f"@{i:040x}\n\n" + "".join(f"{f}\n" for f in files) + "\n"
                   for i, files in enumerate(commits))


class Coupling(unittest.TestCase):
    def test_a_pair_is_listed_once_with_its_shared_commits_and_degree(self):
        text = log(["src/decoder.cpp", "src/link.cpp"], ["src/link.cpp", "src/decoder.cpp"],
                   ["src/decoder.cpp", "src/link.cpp", "README.md"], ["src/decoder.cpp"])
        self.assertEqual(coupling(text)[0], ("src/decoder.cpp", "src/link.cpp", 3, 1.0))
        self.assertEqual(len([r for r in coupling(text) if {r[0], r[1]} == {"src/decoder.cpp",
                                                                             "src/link.cpp"}]), 1)

    def test_a_commit_of_more_than_max_files_adds_nothing(self):
        big = [f"f{i:02}.cpp" for i in range(21)]
        self.assertEqual(coupling(log(big, big), max_files=20), [])
        self.assertEqual(len(coupling(log(big[:20], big[:20]), max_files=20)), 190)

    def test_a_large_commit_does_not_dilute_the_degree(self):
        big = ["a.cpp", "b.cpp"] + [f"f{i:02}.cpp" for i in range(30)]
        text = log(["a.cpp", "b.cpp"], ["a.cpp", "b.cpp"], big)
        self.assertEqual(coupling(text), [("a.cpp", "b.cpp", 2, 1.0)])

    def test_pairs_below_min_shared_are_left_out_and_the_order_is_fixed(self):
        text = log(["a", "b", "c"], ["a", "b", "c"], ["a", "b"], ["c", "d"], ["a", "d"])
        self.assertEqual(coupling(text, min_shared=2),
                         [("a", "b", 3, 1.0), ("a", "c", 2, 2 / 3), ("b", "c", 2, 2 / 3)])

    def test_an_empty_log_gives_nothing(self):
        self.assertEqual(coupling(""), [])


if __name__ == "__main__":
    unittest.main()
