#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/evidence_paths.py (CAPA-0008): evidence names no path of the machine."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence_paths  # noqa: E402

SCRATCH = "/tmp/claude-0/-home-someone/01234567-89ab-cdef-0123-456789abcdef/scratchpad"


class Clean(unittest.TestCase):
    def test_a_scratch_directory_and_a_home_become_names(self):
        text = (f"Test project {SCRATCH}/rc230/build/debug\n"
                "\"executable\": \"/home/someone/detector-to-diagnosis/build/release/bm\"\n"
                "cd /root/src && /Users/x/y\n"
                "out /tmp/claude-0/rel110/coverage\n")
        out = evidence_paths.clean(text)
        self.assertEqual(out, "Test project $SCRATCH/rc230/build/debug\n"
                              "\"executable\": \"~/detector-to-diagnosis/build/release/bm\"\n"
                              "cd ~/src && ~/y\n"
                              "out $SCRATCH/rel110/coverage\n")
        self.assertEqual(evidence_paths.found(out), [])

    def test_a_home_after_a_doubled_slash_is_found(self):
        # MDQ-PR-107: GCC printed a profile directory joined to an absolute object path.
        text = ("data file 'build/pgo-data//home/someone/src/b.gcda' not found\n"
                "see file:///home/someone/report.html\n")
        self.assertEqual(evidence_paths.found(text), ["/home/someone", "/home/someone"])
        self.assertEqual(evidence_paths.clean(text),
                         "data file 'build/pgo-data/~/src/b.gcda' not found\n"
                         "see file://~/report.html\n")

    def test_temporary_and_relative_paths_are_kept(self):
        text = ("run /tmp/tmp.nPtnn2ROtj/out and /tmp/minidaq-e2e-x/run.bin\n"
                "measurements/home/root.txt, build/home/user, ~/src, $HOME/x\n")
        self.assertEqual(evidence_paths.found(text), [])
        self.assertEqual(evidence_paths.clean(text), text)


class Repository(unittest.TestCase):
    def repo(self, d):
        root = pathlib.Path(d)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "measurements/r").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "book").mkdir()
        (root / "measurements/r/ctest.txt").write_text("Test project /home/someone/src/build\n")
        (root / "measurements/r/ok.txt").write_text("Test project build/debug\n")
        (root / "measurements/r/blob.bin").write_bytes(b"\xff\xfe/home/someone\x00")
        (root / "docs/note.md").write_text(f"see {SCRATCH}/out\n")
        (root / "book/ch.md").write_text("cd /home/you/project\n")  # not evidence
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        return root

    def test_check_names_each_path_in_tracked_evidence_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            problems = evidence_paths.check(root)
            self.assertEqual(len(problems), 2, problems)
            self.assertTrue(problems[0].startswith("docs/note.md:1: names /tmp/claude-0/"), problems)
            self.assertTrue(problems[1].startswith("measurements/r/ctest.txt:1: names /home/someone"),
                            problems)

    def test_fix_leaves_nothing_for_check_and_binary_files_alone(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.assertEqual(evidence_paths.fix(root / "measurements"), 1)
            self.assertEqual(evidence_paths.fix(root / "docs"), 1)
            self.assertEqual(evidence_paths.check(root), [])
            self.assertEqual((root / "measurements/r/ctest.txt").read_text(), "Test project ~/src/build\n")
            self.assertEqual((root / "measurements/r/blob.bin").read_bytes(), b"\xff\xfe/home/someone\x00")

    def test_fix_keeps_the_line_endings_of_a_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "perf.txt"
            f.write_bytes(b"a /home/someone/b\r\nc\rd\n")
            evidence_paths.fix(d)
            self.assertEqual(f.read_bytes(), b"a ~/b\r\nc\rd\n")

    def test_the_command_fails_on_a_path_and_passes_when_fixed(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            tool = [sys.executable, str(HERE / "evidence_paths.py")]
            self.assertEqual(subprocess.run(tool + ["check", str(root)], capture_output=True).returncode, 1)
            subprocess.run(tool + ["fix", str(root / "measurements"), str(root / "docs")],
                           capture_output=True, check=True)
            self.assertEqual(subprocess.run(tool + ["check", str(root)], capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(tool, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
