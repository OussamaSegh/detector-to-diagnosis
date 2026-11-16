#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/release_checks.sh that do not run the checks (MDQ-PR-029).

The script stopped after the writer benchmark of releases 0.3.0 and 0.4.0 with status 0: an
`exit` inside a { } group ends the whole script. These tests read the script for that mistake
and run its end-of-run guard on its own."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent / "release_checks.sh"
STRESS = pathlib.Path(__file__).resolve().parent / "stress_tests.sh"


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


def resume(out, failing_part=None):
    """Runs the script's resume block with a stub for "$0" that records each part it is asked
    to run (and fails on failing_part), so no check runs."""
    lines = SCRIPT.read_text().splitlines()
    first = next(i for i, x in enumerate(lines) if x.startswith('if [ "$part" = resume ]'))
    last = next(i for i in range(first, len(lines)) if lines[i] == "fi")
    block = "\n".join(lines[first:last + 1]).replace('"$0"', "stub")
    stub = ('stub() { echo "ran part $3" >> "$1/ran"; '
            f'[ "$3" = "{failing_part}" ] && return 1; '
            'echo "all release checks passed (part $3)" >> "$1/release-checks.txt"; }\n')
    return subprocess.run(["bash", "-c", f"set -uo pipefail\nout={out}\nfuzz_seconds=1\npart=resume\n"
                           + stub + block], capture_output=True, text=True)


class ReleaseChecks(unittest.TestCase):
    def test_resume_runs_only_the_parts_not_yet_passed(self):
        with tempfile.TemporaryDirectory() as out:
            path = pathlib.Path(out)
            (path / "release-checks.txt").write_text(
                "## part 1\nall release checks passed (part 1)\n## part 2\n1 release checks failed (part 2)\n")
            (path / "rerun-part-2.md").write_text("investigated\n")
            p = resume(out)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual((path / "ran").read_text(), "ran part 2\nran part 3\nran part 4\n")
            # Run again after everything passed: nothing runs.
            (path / "ran").unlink()
            self.assertEqual(resume(out).returncode, 0)
            self.assertFalse((path / "ran").exists())

    def test_resume_stops_at_the_first_failing_part(self):
        with tempfile.TemporaryDirectory() as out:
            p = resume(out, failing_part=2)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual((pathlib.Path(out) / "ran").read_text(), "ran part 1\nran part 2\n")

    def test_a_failed_part_runs_again_only_after_its_investigation(self):
        # SDP section 8 (MDQ-PR-077): investigate first, write it down, then run once more.
        with tempfile.TemporaryDirectory() as out:
            path = pathlib.Path(out)
            (path / "release-checks.txt").write_text(
                "all release checks passed (part 1)\nall release checks passed (part 2)\n"
                "1 release checks failed (part 3)\n")
            p = resume(out)
            self.assertEqual(p.returncode, 4)
            self.assertIn("rerun-part-3.md", p.stderr)
            self.assertFalse((path / "ran").exists())
            (path / "rerun-part-3.md").write_text("The gate's verdict on BM_X: same machine code.\n")
            p = resume(out)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual((path / "ran").read_text(), "ran part 3\nran part 4\n")

    def test_a_part_that_failed_twice_does_not_run_a_third_time(self):
        with tempfile.TemporaryDirectory() as out:
            path = pathlib.Path(out)
            (path / "release-checks.txt").write_text(
                "1 release checks failed (part 2)\n2 release checks failed (part 2)\n"
                "all release checks passed (part 1)\n")
            (path / "rerun-part-2.md").write_text("investigated\n")
            p = resume(out)
            self.assertEqual(p.returncode, 4)
            self.assertIn("failed twice", p.stderr)
            self.assertFalse((path / "ran").exists())

    def test_a_part_that_stopped_without_a_verdict_runs_again(self):
        # A restart is not a failure: no summary line, so no investigation is asked for.
        with tempfile.TemporaryDirectory() as out:
            path = pathlib.Path(out)
            (path / "release-checks.txt").write_text("all release checks passed (part 1)\npass  something\n")
            self.assertEqual(resume(out).returncode, 0)
            self.assertEqual((path / "ran").read_text(), "ran part 2\nran part 3\nran part 4\n")

    def test_a_whole_run_that_passed_counts_for_every_part(self):
        with tempfile.TemporaryDirectory() as out:
            (pathlib.Path(out) / "release-checks.txt").write_text("all release checks passed (part all)\n")
            self.assertEqual(resume(out).returncode, 0)
            self.assertFalse((pathlib.Path(out) / "ran").exists())

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
        p = subprocess.run(["bash", str(SCRIPT), "/nonexistent/out", "600", "5"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("PART is all, resume, 1, 2, 3 or 4", p.stderr)

    def test_a_part_ends_with_its_summary(self):
        text = SCRIPT.read_text()
        for n in (1, 2, 3):
            self.assertIn(f'[ "$part" = {n} ] && summary', text)
        self.assertTrue(text.rstrip().endswith("summary"))

    def test_each_part_runs_only_its_own_checks(self):
        # Every check is inside one part's block, so a part never runs another's checks
        # (MDQ-PR-041). The blocks open in order, 1 to 4, and each closes before the next.
        lines = SCRIPT.read_text().splitlines()
        opened = [n for n, x in enumerate(lines) if re.fullmatch(r"if in_part [1-4]; then", x)]
        self.assertEqual([lines[n][-7] for n in opened], ["1", "2", "3", "4"])
        depth = 0
        for n, x in enumerate(lines):
            if re.fullmatch(r"if in_part [1-4]; then", x):
                self.assertEqual(depth, 0, f"line {n + 1}: a part inside a part")
                depth = 1
            elif x == "fi" and depth:
                depth = 0
            elif x.startswith("check ") and opened[0] < n:
                self.assertEqual(depth, 1, f"line {n + 1}: a check outside every part")

    def test_a_dirty_tree_keeps_its_own_status(self):
        self.assertEqual(run_bash("exit 2\n").returncode, 2)



@unittest.skipUnless(shutil.which("ctest"), "ctest not installed")
class StressRun(unittest.TestCase):
    """tools/stress_tests.sh, which the release checks run (MDQ-PR-032)."""

    def run_stress(self, tests):
        with tempfile.TemporaryDirectory() as d:
            build = pathlib.Path(d)
            (build / "CTestTestfile.cmake").write_text(
                "".join(f'add_test({name} "{cmd}")\n' for name, cmd in tests))
            out = build / "stress.txt"
            p = subprocess.run(["sh", str(STRESS), str(build), "2", str(out), "^t_"],
                               capture_output=True, text=True)
            return p.returncode, out.read_text()

    def test_a_failed_test_fails_the_stress_run(self):
        status, text = self.run_stress([("t_fail", "false"), ("t_ok", "true")])
        self.assertNotEqual(status, 0)
        self.assertIn("t_fail (Failed)", text)

    def test_passing_tests_pass(self):
        status, text = self.run_stress([("t_ok", "true")])
        self.assertEqual(status, 0, text)
        self.assertIn("100% tests passed", text)


if __name__ == "__main__":
    unittest.main()
