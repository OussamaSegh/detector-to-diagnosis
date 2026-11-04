#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/survey.py (Chapter 34), run by CTest as tools.survey.

The parsing of git's numstat output and the item map's ownership rule are tested on strings; the
whole survey on a small repository made for the test, with two items, three requirements, a
problem report and a history of three commits.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import survey  # noqa: E402

ITEMS = [{"id": "sorter", "class": "B", "hazards": ["HZ-1"],
          "paths": ["minidaq/src/processing/coincidence_sorter"]},
         {"id": "processing", "class": "B", "hazards": ["HZ-1"],
          "paths": ["minidaq/src/processing/"]},
         {"id": "tools", "class": None, "paths": ["minidaq/apps/minidaq_sim"]}]


class Churn(unittest.TestCase):
    def test_counts_commits_and_changed_lines_per_file(self):
        # REQ: SRS-SVY-001
        text = ("@1111\n\n3\t1\tminidaq/src/a.cpp\n10\t0\tminidaq/src/b.cpp\n"
                "@2222\n\n2\t2\tminidaq/src/a.cpp\n")
        self.assertEqual(survey.churn(text), {"minidaq/src/a.cpp": (2, 8),
                                              "minidaq/src/b.cpp": (1, 10)})

    def test_a_renamed_file_counts_under_its_new_name(self):
        # REQ: SRS-SVY-001
        text = ("@1\n\n1\t1\tminidaq/src/{old => new}/a.cpp\n"
                "@2\n\n4\t0\tminidaq/src/new/a.cpp\n@3\n\n0\t0\tdoc.md => notes.md\n")
        self.assertEqual(survey.churn(text), {"minidaq/src/new/a.cpp": (2, 6), "notes.md": (1, 0)})
        self.assertEqual(survey.renamed_to("a/{b => }/c.cpp"), "a/c.cpp")

    def test_a_binary_file_counts_its_commits_and_no_lines(self):
        # REQ: SRS-SVY-001
        self.assertEqual(survey.churn("@1\n\n-\t-\tlogo.png\n@2\n\n-\t-\tlogo.png\n"),
                         {"logo.png": (2, 0)})

    def test_code_lines_leave_out_blank_lines_and_comments(self):
        text = "// SPDX\n\n#include <x>\nint f() {\n  return 1;  // one\n}\n# a comment\n"
        self.assertEqual(survey.code_lines(text), 3)


class Owners(unittest.TestCase):
    def test_the_longest_prefix_owns_a_file(self):
        # REQ: SRS-SVY-002
        self.assertEqual(survey.owners("minidaq/src/processing/coincidence_sorter.cpp", ITEMS),
                         ["sorter", "processing"])
        self.assertEqual(survey.owners("minidaq/src/processing/sinogram.cpp", ITEMS),
                         ["processing"])
        self.assertEqual(survey.owners("minidaq/src/net/socket.cpp", ITEMS), [])

    def test_two_prefixes_of_the_same_length_are_ambiguous(self):
        # REQ: SRS-SVY-002
        items = ITEMS + [{"id": "other", "paths": ["minidaq/src/processing/"]}]
        self.assertTrue(survey.ambiguous("minidaq/src/processing/sinogram.cpp", items))
        self.assertFalse(survey.ambiguous("minidaq/src/processing/coincidence_sorter.cpp", items))
        self.assertFalse(survey.ambiguous("minidaq/src/net/socket.cpp", items))


SRS = """| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SRT-001 | The sorter shall pair singles. | sorter | T |
| SRS-SRT-002 | The sorter shall count. | sorter | T |
| SRS-PROC-001 | The energy filter shall be inspected. | processing | I |
"""


class Repository:
    """A git repository with two product items, its documents and three commits."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        self.git("init", "-q")
        self.write("docs/architecture/software-items.json", json.dumps({"items": ITEMS}))
        self.write("docs/regulatory/srs.md", SRS)
        self.write("docs/regulatory/problem-reports.json", json.dumps({"reports": [
            {"id": "MDQ-PR-001", "item": "sorter", "status": "open"},
            {"id": "MDQ-PR-002", "item": "sorter", "status": "closed"}]}))
        tag = "RE" + "Q: SRS-SRT-001"  # split, so that the trace matrix does not read it here
        self.write("minidaq/tests/test_sorter.cpp", f"TEST(S, Pairs) {{}}  // {tag}\n")
        self.write("minidaq/src/processing/coincidence_sorter.cpp", "int a;\nint b;\n")
        self.write("minidaq/src/processing/sinogram.cpp", "int c;\n")
        self.commit("first")
        self.write("minidaq/src/processing/coincidence_sorter.cpp", "int a;\nint b;\nint d;\n")
        self.commit("second")
        self.write("minidaq/src/processing/coincidence_sorter.cpp", "int a;\nint d;\n")
        self.commit("third")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=self.env,
                       capture_output=True)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def close(self):
        self._tmp.cleanup()


class Survey(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def tearDown(self):
        self.repo.close()

    def test_each_item_gets_its_documents_and_its_history(self):
        # REQ: SRS-SVY-003
        s = survey.survey(self.repo.root, "10 years ago")
        rows = {r["item"]: r for r in s["items"]}
        sorter, processing = rows["sorter"], rows["processing"]
        self.assertEqual((sorter["files"], sorter["code_lines"], sorter["commits"]), (1, 2, 3))
        self.assertEqual(sorter["changed_lines"], 2 + 1 + 1)
        self.assertEqual((sorter["requirements"], sorter["by_test"], sorter["tested"]), (2, 2, 1))
        self.assertEqual((sorter["reports"], sorter["open_reports"]), (2, 1))
        self.assertEqual((processing["files"], processing["commits"]), (1, 1))
        self.assertEqual((processing["requirements"], processing["by_test"]), (1, 0))

    def test_hotspots_are_ranked_by_commits_times_code_lines(self):
        # REQ: SRS-SVY-003
        s = survey.survey(self.repo.root, "10 years ago")
        self.assertEqual([(h["file"], h["score"]) for h in s["hotspots"]],
                         [("minidaq/src/processing/coincidence_sorter.cpp", 6),
                          ("minidaq/src/processing/sinogram.cpp", 1)])

    def test_the_report_names_an_untested_requirement_and_exits_0(self):
        # REQ: SRS-SVY-003
        out = self.run_main()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("| sorter | B | HZ-1 | 1 | 2 | 3 | 4 | 2 (2, 1) | 2 (1) |", out.stdout)
        self.assertIn("no test names: sorter.", out.stdout)
        self.assertIn("Prefixes that claim no file: tools `minidaq/apps/minidaq_sim`.", out.stdout)

    def test_a_product_file_no_item_claims_fails(self):
        # REQ: SRS-SVY-002
        self.repo.write("minidaq/src/net/socket.cpp", "int s;\n")
        self.repo.commit("unclaimed")
        out = self.run_main()
        self.assertEqual(out.returncode, 1)
        self.assertIn("Files no item claims: `minidaq/src/net/socket.cpp`.", out.stdout)

    def run_main(self):
        return subprocess.run([sys.executable, str(pathlib.Path(survey.__file__)),
                               str(self.repo.root), "--since", "10 years ago"],
                              capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
