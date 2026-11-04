#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/ai_provenance.py and of the commit policy's rule assisted (Chapter 37), run by
CTest as tools.ai_provenance.

The trailers and the items are tested on strings and dictionaries; the report and the rule on a
small repository made for the test, with two product items, a test directory and a history of
assisted and unassisted commits.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ai_provenance as ap  # noqa: E402
import check_commits as cc  # noqa: E402

POLICY = json.loads((pathlib.Path(__file__).resolve().parent / "commit_policy.json").read_text())
ITEMS = [{"id": "sorter", "class": "B", "paths": ["minidaq/src/processing/coincidence_sorter"]},
         {"id": "processing", "class": "B", "paths": ["minidaq/src/processing/"]},
         {"id": "tools", "class": None, "paths": ["tools/"]}]
ASSISTANT = "Co-Authored-By: An Assistant <noreply@anthropic.com>"
REVIEW = "Review: change control checklist, items 1 to 6."


def message(subject, *trailers):
    return f"{subject}\n\nBody.\n\n" + "\n".join(trailers) + "\n"


class Assisted(unittest.TestCase):
    def test_an_assistant_is_named_in_a_trailer_git_parses(self):
        # REQ: SRS-AI-001
        self.assertEqual(ap.assistant_of(message("Fix", REVIEW, ASSISTANT), POLICY),
                         "An Assistant <noreply@anthropic.com>")
        self.assertEqual(ap.assistant_of(message("Fix", "assisted-by: Copilot"), POLICY),
                         "Copilot")
        self.assertIsNone(ap.assistant_of(message("Fix", REVIEW), POLICY))
        human = message("Fix", "Co-Authored-By: A Person <person@example.org>")
        self.assertIsNone(ap.assistant_of(human, POLICY))
        above = f"Fix\n\nBody.\n\n{ASSISTANT}\n\n{REVIEW}\n"  # not in the trailer block
        self.assertIsNone(ap.assistant_of(above, POLICY))
        prose = message("Fix", "Reviewed-by: someone who mentioned noreply@anthropic.com")
        self.assertIsNone(ap.assistant_of(prose, POLICY))

    def test_product_code_belongs_to_the_item_with_the_longest_prefix(self):
        # REQ: SRS-AI-002
        files = ["minidaq/src/processing/coincidence_sorter.cpp",
                 "minidaq/src/processing/sinogram.cpp", "minidaq/tests/unit/test_sorter.cpp",
                 "tools/survey.py", "docs/regulatory/srs.md", "minidaq/src/processing/README.md"]
        self.assertEqual(ap.touched({"files": files}, ITEMS), {"sorter": "B", "processing": "B"})
        for path in ("minidaq/tests/unit/test_sorter.cpp", "tools/test_survey.py",
                     "exercises/ch10/e1/tests/test_x.py"):
            self.assertTrue(ap.is_test(path), path)
        self.assertFalse(ap.is_test("minidaq/src/processing/testing_helpers.cpp"))


class Repository:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q", "-b", "main")
        self.write("docs/architecture/software-items.json", json.dumps({"items": ITEMS}))
        self.write("docs/regulatory/srs.md", "")
        self.write("tools/commit_policy.json", json.dumps(POLICY))
        self.commit(message("Start", REVIEW))
        self.since = self.head()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, env=self.env,
                              capture_output=True, text=True).stdout

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, text):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", text)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def close(self):
        self._tmp.cleanup()


class Report(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        r = self.repo
        r.write("minidaq/src/processing/coincidence_sorter.cpp", "int a;\n")
        r.write("minidaq/tests/unit/test_sorter.cpp", "TEST(S, A) {}\n")
        self.with_test = r.commit(message("Sorter: pairs", REVIEW, ASSISTANT))
        r.write("minidaq/src/processing/coincidence_sorter.cpp", "int b;\n")
        self.without = r.commit(message("Sorter: rename", REVIEW, ASSISTANT))
        r.write("minidaq/src/processing/sinogram.cpp", "int c;\n")
        self.named = r.commit(message("Sinogram: bins", REVIEW, "Tests: Sinogram.Bins",
                                      ASSISTANT))
        r.write("minidaq/src/processing/sinogram.cpp", "int d;\n")
        self.human = r.commit(message("Sinogram: by hand", REVIEW))
        r.write("tools/survey.py", "x = 1\n")
        self.tool = r.commit(message("Survey: a tool", REVIEW, ASSISTANT))

    def tearDown(self):
        self.repo.close()

    def test_counts_and_lists_the_assisted_product_changes_without_a_test(self):
        # REQ: SRS-AI-003
        r = ap.report(self.repo.root, f"{self.repo.since}..HEAD", POLICY)
        self.assertEqual((r["commits"], r["assisted"], r["assisted_with_product_code"]), (5, 4, 3))
        self.assertEqual(r["assisted_product_code_without_a_test"],
                         [self.without[:12], self.named[:12]])
        self.assertEqual(r["assisted_per_item"], {"processing": 1, "sorter": 2})
        self.assertEqual(r["assisted_with_a_parsed_review_trailer"], 4)
        out = subprocess.run([sys.executable, ap.__file__, str(self.repo.root),
                              f"{self.repo.since}..HEAD", "--json"],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)["assisted"], 4)

    def test_the_policy_rule_wants_a_test_or_a_tests_trailer(self):
        # REQ: SRS-AI-004
        known = cc.known_references(self.repo.root)
        found = {c["sha"]: cc.assisted(c, POLICY, known)
                 for c in cc.commits(self.repo.root, f"{self.repo.since}..HEAD")}
        self.assertEqual([sha for sha, p in found.items() if p], [self.without])
        self.assertIn("sorter", found[self.without][0])
        self.assertIn("'Tests:'", found[self.without][0])


if __name__ == "__main__":
    unittest.main()
