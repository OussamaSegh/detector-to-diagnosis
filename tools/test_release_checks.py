#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/release_checks.sh that do not run the checks (MDQ-PR-029).

The script stopped after the writer benchmark of releases 0.3.0 and 0.4.0 with status 0: an
`exit` inside a { } group ends the whole script. These tests read the script for that mistake
and run its end-of-run guard on its own."""
import pathlib
import re
import subprocess
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent / "release_checks.sh"


def groups_with_exit(text):
    """The first line numbers of the top-level { } groups that contain an exit."""
    found, start = [], None
    for n, line in enumerate(text.splitlines(), 1):
        if start is None and line.startswith("{"):
            start = n
        if start is not None:
            if re.search(r"(^|[;&|\s])exit\b", line):
                found.append(start)
                start = None
            elif re.search(r"\}\s*(>|$)", line):
                start = None
    return found


def guard():
    """The lines of the script from the work directory to the trap: the end-of-run guard."""
    lines = SCRIPT.read_text().splitlines()
    first = next(i for i, x in enumerate(lines) if x.startswith("work=$(mktemp"))
    last = next(i for i, x in enumerate(lines) if x.startswith("trap on_exit EXIT"))
    return "\n".join(lines[first:last + 1])


def run_bash(body):
    return subprocess.run(["bash", "-c", "set -uo pipefail\n" + guard() + "\n" + body],
                          capture_output=True, text=True)


class ReleaseChecks(unittest.TestCase):
    def test_no_group_of_the_script_exits(self):
        self.assertEqual(groups_with_exit(SCRIPT.read_text()), [])

    def test_the_reader_finds_the_old_mistake(self):
        old = '{ stamp "writer"\n  status=0\n  exit $status; } > "$out/perf-writer.txt"\n'
        self.assertEqual(groups_with_exit(old), [1])
        self.assertEqual(groups_with_exit('( stamp "writer"\n  exit $status ) > out\n'), [])

    def test_a_run_that_stops_early_fails(self):
        p = run_bash("{ exit 0; }\nfinished=yes\n")
        self.assertEqual(p.returncode, 3)
        self.assertIn("stopped before the last check", p.stdout)

    def test_a_run_that_reaches_the_end_keeps_its_status(self):
        self.assertEqual(run_bash("finished=yes\nexit 0\n").returncode, 0)
        self.assertEqual(run_bash("finished=yes\nexit 1\n").returncode, 1)

    def test_an_unknown_part_is_refused_before_anything_runs(self):
        p = subprocess.run(["bash", str(SCRIPT), "/nonexistent/out", "600", "3"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("PART is all, 1 or 2", p.stderr)

    def test_a_part_ends_with_its_summary(self):
        text = SCRIPT.read_text()
        self.assertIn('[ "$part" = 1 ] && summary', text)
        self.assertTrue(text.rstrip().endswith("summary"))

    def test_a_dirty_tree_keeps_its_own_status(self):
        self.assertEqual(run_bash("exit 2\n").returncode, 2)


if __name__ == "__main__":
    unittest.main()
