# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 34.4, on histories written as `git log --numstat` prints them."""
import unittest

import hotspots as hs


def log(*commits):
    """commits: (hash, date, [path, ...]); every file gets 1 line added and 1 deleted."""
    out = []
    for h, date, paths in commits:
        out.append(f"commit {h} {date}")
        out.extend(f"1\t1\t{p}" for p in paths)
        out.append("")
    return "\n".join(out) + "\n"


SIZES = {"src/service.cpp": 500, "src/sorter.cpp": 300, "src/config.cpp": 60, "big/table.cpp": 4000}


class Hotspots(unittest.TestCase):
    def test_commits_times_lines_highest_first(self):
        text = log(("c3", "2026-03-01", ["src/service.cpp", "src/config.cpp"]),
                   ("c2", "2026-02-01", ["src/service.cpp", "src/sorter.cpp"]),
                   ("c1", "2026-01-01", ["src/config.cpp", "src/sorter.cpp"]))
        ranking, mass = hs.hotspots(text, SIZES)
        self.assertEqual([r[0] for r in ranking],
                         ["src/service.cpp", "src/sorter.cpp", "src/config.cpp", "big/table.cpp"])
        self.assertEqual(ranking[0], ("src/service.cpp", 2, 500, 1000))
        self.assertEqual(ranking[-1], ("big/table.cpp", 0, 4000, 0))
        self.assertEqual(mass, [])

    def test_a_commit_that_touches_everything_is_left_out(self):
        reformat = [f"src/f{k}.cpp" for k in range(30)] + ["big/table.cpp"]
        text = log(("r", "2026-03-01", reformat),
                   ("c1", "2026-02-01", ["src/service.cpp"]))
        ranking, mass = hs.hotspots(text, SIZES, mass=20)
        self.assertEqual(mass, ["r"])
        self.assertEqual(ranking[0][0], "src/service.cpp")
        self.assertEqual(dict((r[0], r[1]) for r in ranking)["big/table.cpp"], 0)

    def test_renames_are_followed_to_the_current_name(self):
        self.assertEqual(hs.rename("src/{old => new}/a.cpp"), ("src/old/a.cpp", "src/new/a.cpp"))
        self.assertEqual(hs.rename("src/{ => core}/a.cpp"), ("src/a.cpp", "src/core/a.cpp"))
        self.assertEqual(hs.rename("a.cpp => b.cpp"), ("a.cpp", "b.cpp"))
        self.assertEqual(hs.rename("src/a.cpp"), ("src/a.cpp", "src/a.cpp"))
        text = log(("c4", "2026-04-01", ["src/{run_service.cpp => service.cpp}"]),
                   ("c3", "2026-03-01", ["src/run_service.cpp"]),
                   ("c2", "2026-02-01", ["{acq => src}/run_service.cpp"]),
                   ("c1", "2026-01-01", ["acq/run_service.cpp", "src/sorter.cpp"]))
        ranking, _ = hs.hotspots(text, SIZES)
        counts = dict((r[0], r[1]) for r in ranking)
        self.assertEqual(counts["src/service.cpp"], 4)
        self.assertEqual(counts["src/sorter.cpp"], 1)
        self.assertEqual(len(ranking), len(SIZES))  # old names are not files any more

    def test_the_window_and_binary_files(self):
        text = (log(("c2", "2026-06-01", ["src/sorter.cpp"])) + "commit c1 2025-12-31\n"
                "-\t-\tsrc/sorter.cpp\n1\t0\tsrc/service.cpp\n")
        ranking, _ = hs.hotspots(text, SIZES, since="2026-01-01")
        counts = dict((r[0], r[1]) for r in ranking)
        self.assertEqual(counts["src/sorter.cpp"], 1)
        self.assertEqual(counts["src/service.cpp"], 0)
        ranking, _ = hs.hotspots(text, SIZES)
        self.assertEqual(dict((r[0], r[1]) for r in ranking)["src/sorter.cpp"], 2)

    def test_equal_scores_are_ordered_by_path(self):
        sizes = {"b.cpp": 10, "a.cpp": 10}
        ranking, _ = hs.hotspots(log(("c1", "2026-01-01", ["a.cpp", "b.cpp"])), sizes)
        self.assertEqual([r[0] for r in ranking], ["a.cpp", "b.cpp"])


if __name__ == "__main__":
    unittest.main()
