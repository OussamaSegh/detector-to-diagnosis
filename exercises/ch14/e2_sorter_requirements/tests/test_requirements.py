"""Acceptance tests for Exercise 14.2: the requirement linter and 20 sorter requirements."""
import pathlib
import re
import unittest

import req_lint

VARIANT = pathlib.Path(req_lint.__file__).resolve().parent


def issues(text, method="T"):
    return req_lint.problems("SRS-SRT-001", text, method)


class Linter(unittest.TestCase):
    def test_a_good_requirement_passes(self):
        self.assertEqual(issues("The sorter shall pair two singles at most 4000 ps apart."), [])
        self.assertEqual(issues("When the policy is `kill_all`, the sorter shall discard the window."), [])

    def test_one_requirement_per_row(self):
        self.assertTrue(issues("The sorter shall sort and the writer shall write."))
        self.assertTrue(issues("The sorter sorts singles."))

    def test_vague_words_are_reported(self):
        for text in ("The sorter shall be fast.", "The sorter shall handle multiples appropriately.",
                     "The sorter shall be robust against bad input.", "The sorter shall support A and/or B."):
            self.assertTrue(any("vague" in p for p in issues(text)), text)

    def test_optional_words_are_reported(self):
        self.assertTrue(issues("The sorter should reject late singles."))

    def test_a_number_needs_its_unit(self):
        self.assertTrue(any("unit" in p for p in issues("The sorter shall use a window of 4000.")))
        self.assertFalse(any("unit" in p for p in issues("The sorter shall use a window of 4000 ps.")))
        self.assertFalse(any("unit" in p for p in issues("The sorter shall count 24 sectors.")))
        self.assertFalse(any("unit" in p for p in issues("The sorter shall read schema version 1.3.")))

    def test_the_method_is_required(self):
        self.assertTrue(issues("The sorter shall pair singles.", method=""))
        self.assertTrue(issues("The sorter shall pair singles.", method="X"))
        self.assertEqual(issues("The sorter shall pair singles.", method="T, M"), [])

    def test_duplicate_ids_are_reported(self):
        doc = "| SRS-SRT-001 | The sorter shall pair singles. | sorter | T |\n" * 2
        self.assertTrue(any("duplicate" in p for _, _, p in req_lint.lint(doc)))


TOPICS = {
    "the window and its edge": r"\bwindow\b.*\bps\b",
    "fixed and per-single windows": r"per_single|per single",
    "every multiples policy": r"kill_all.*|take_all_goods|take_winner_of_goods",
    "the energy gate": r"\bkeV\b",
    "the sector cut": r"\bsectors?\b",
    "the field of view": r"field.of.view.*\bmm\b",
    "delayed coincidences": r"\bdelayed\b",
    "out-of-order singles": r"\b(earlier than|out of order)\b",
    "batch independence": r"\bbatch",
    "accounting of every single": r"\b(account|counters?)\b",
    "configuration errors": r"\b(refuse|reject)\b.*\bconfiguration\b|\bconfiguration\b.*\b(refuse|reject)",
    "throughput": r"singles/s",
    "latency": r"\bat the latest\b|\bwithin\b.*\b(ns|ps|us|ms)\b",
}


class SorterRequirements(unittest.TestCase):
    def setUp(self):
        self.text = (VARIANT / "sorter-requirements.md").read_text()
        self.reqs = req_lint.requirements(self.text)

    def test_at_least_twenty_requirements(self):
        self.assertGreaterEqual(len(self.reqs), 20)

    def test_every_requirement_passes_the_linter(self):
        self.assertEqual(req_lint.lint(self.text), [])

    def test_they_cover_the_sorter(self):
        bodies = [r[2] for r in self.reqs]
        for topic, pattern in TOPICS.items():
            self.assertTrue(any(re.search(pattern, b) for b in bodies), f"no requirement covers {topic}")
        for policy in ("kill_all", "take_all_goods", "take_winner_of_goods", "keep_if_only_one_good"):
            self.assertTrue(any(policy in b for b in bodies), f"no requirement for {policy}")

    def test_most_are_verified_by_test(self):
        tested = [r for r in self.reqs if "T" in r[4]]
        self.assertGreaterEqual(len(tested), 0.8 * len(self.reqs))


if __name__ == "__main__":
    unittest.main()
