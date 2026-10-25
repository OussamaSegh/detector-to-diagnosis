"""Acceptance tests for Exercise 14.5: the release record check."""
import pathlib
import unittest

import release_check

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixture"
GOOD = (FIXTURE / "release-record.md").read_text()


def errors(text):
    return release_check.check(text, FIXTURE)


class ReleaseRecord(unittest.TestCase):
    def test_a_complete_record_allows_the_release(self):
        self.assertEqual(errors(GOOD), [])

    def test_every_section_is_required(self):
        for name in release_check.SECTIONS:
            text = GOOD.replace(f"## {name}\n", "## Something else\n")
            self.assertTrue(any(name in e for e in errors(text)), name)

    def test_the_tag_matches_the_version(self):
        self.assertTrue(errors(GOOD.replace("tag book-v0.3.0", "tag book-v0.2.0")))
        self.assertTrue(errors(GOOD.replace("commit 0123456789abcdef", "commit 0123")))

    def test_every_check_of_the_plan_has_a_row(self):
        text = GOOD.replace("| tests tsan | pass | logs/tests-tsan.log |\n", "")
        self.assertTrue(any("'tests tsan'" in e for e in errors(text)))

    def test_a_check_that_did_not_pass_blocks_the_release(self):
        for result in ("fail", "skipped", "pass (2 flaky)", ""):
            text = GOOD.replace("| fuzzing | pass |", f"| fuzzing | {result} |")
            self.assertTrue(any("'fuzzing'" in e for e in errors(text)), result)

    def test_evidence_must_exist(self):
        text = GOOD.replace("logs/perf.txt", "logs/perf-final.txt")
        self.assertTrue(any("'performance'" in e and "not a file" in e for e in errors(text)))
        text = GOOD.replace("| trace matrix | pass | logs/trace.txt |", "| trace matrix | pass |  |")
        self.assertTrue(any("'trace matrix'" in e for e in errors(text)))

    def test_every_open_problem_report_is_listed(self):
        text = GOOD.replace("MDQ-PR-005 and ", "")
        self.assertTrue(any("MDQ-PR-005" in e for e in errors(text)))

    def test_the_soup_review_is_dated_and_the_build_repeatable(self):
        self.assertTrue(errors(GOOD.replace("reviewed 2026-10-25", "reviewed last week")))
        self.assertTrue(errors(GOOD.replace("cmake --preset hardened", "the usual build")))


if __name__ == "__main__":
    unittest.main()
