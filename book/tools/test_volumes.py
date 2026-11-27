#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of book/tools/volumes.py (roadmap 3.0.0, Theme K), and the check of book/book.txt."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import volumes  # noqa: E402

LIST = """# comment
#volume 1: The System and the Process
src/front/edition.md
src/part1/part1.md
src/part1/ch01-a.md
src/part5/ch25-b.md

#volume 2: From Data to Diagnosis
src/part6/part6.md
src/part6/ch26-c.md
src/appendix/architecture.md
"""


class Volumes(unittest.TestCase):
    def write(self, d, text, files=()):
        root = pathlib.Path(d)
        (root / "book.txt").write_text(text)
        for name, body in files:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(body)
        return root / "book.txt"

    def test_the_markers_split_the_list(self):
        with tempfile.TemporaryDirectory() as d:
            v = volumes.read(self.write(d, LIST))
            self.assertEqual([(n, t, len(f)) for n, t, f in v],
                             [(1, "The System and the Process", 4), (2, "From Data to Diagnosis", 3)])
            self.assertEqual(volumes.problems(v), [])
            self.assertEqual(volumes.offset(v, 2), 25)
            self.assertEqual(volumes.offset(v, 1), 0)

    def test_a_list_without_markers_is_one_volume(self):
        with tempfile.TemporaryDirectory() as d:
            v = volumes.read(self.write(d, "src/a.md\nsrc/b.md\n"))
            self.assertEqual(len(v), 1)
            self.assertEqual(volumes.problems(v), [])

    def test_problems_are_found(self):
        with tempfile.TemporaryDirectory() as d:
            v = volumes.read(self.write(d, "#volume 1: A\nsrc/a.md\n#volume 3: B\nsrc/a.md\n#volume 4: C\n"))
            text = " ".join(volumes.problems(v))
            self.assertIn("not 1 to 3", text)
            self.assertIn("src/a.md is in volume 1 and volume 3", text)
            self.assertIn("volume 4 has no files", text)

    def test_ids_name_the_volume_that_defines_them(self):
        with tempfile.TemporaryDirectory() as d:
            lst = self.write(d, "#volume 1: A\nsrc/a.md\n#volume 2: B\nsrc/b.md\n", [
                ("src/a.md", "# One {#ch01}\n```{.figure #fig-ch01-x src=\"x\"}\n```\nsee [](#ch02)\n"),
                ("src/b.md", "# Two {#ch02}\n[text]{#sec-two}\n")])
            self.assertEqual(volumes.ids(volumes.read(lst), lst.parent),
                             {"ch01": 1, "fig-ch01-x": 1, "ch02": 2, "sec-two": 2})

    def test_the_command_checks_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            lst = self.write(d, LIST)
            tool = [sys.executable, str(HERE / "volumes.py")]
            run = lambda *a: subprocess.run(tool + list(a), capture_output=True, text=True)
            self.assertEqual(run("check", str(lst)).returncode, 0)
            self.assertEqual(run("count", str(lst)).stdout.strip(), "2")
            self.assertEqual(run("files", str(lst), "2").stdout.split()[0], "src/part6/part6.md")
            self.assertEqual(run("title", str(lst), "1").stdout.strip(), "The System and the Process")
            self.assertEqual(run().returncode, 2)

    def test_the_book_list_is_well_formed(self):
        lst = HERE.parent / "book.txt"
        v = volumes.read(lst)
        self.assertEqual(volumes.problems(v), [])
        self.assertEqual(len(v), 2)
        self.assertEqual(v[1][2][0], "src/part6/part6.md")  # Volume 2 opens with Part VI


if __name__ == "__main__":
    unittest.main()
