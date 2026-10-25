"""Acceptance tests for Exercise 16.2: the two new rules, and the change request for a 3 ns window."""
import json
import pathlib
import unittest

import change

HERE = pathlib.Path(__file__).resolve().parent
KNOWN = {k: set(v) for k, v in json.loads((HERE / "known.json").read_text()).items() if k != "comment"}
NAME = "CR-0010-coincidence-window-3ns.md"


def minimal(status="proposed", commits="none yet", decision="pending", verification="A new test."):
    body = "\n\n".join(f"## {s}\n\nText." if s != "Verification" else f"## {s}\n\n{verification}"
                       for s in change.SECTIONS)
    return (f"# CR-0010: Minimal\n\n| Field | Value |\n|---|---|\n| Status | {status} |\n"
            f"| Requested | 2026-10-25, by the lead |\n| Source | improvement |\n| Decision | {decision} |\n"
            f"| Commits | {commits} |\n\n{body}\n")


class Rules(unittest.TestCase):
    def test_a_minimal_request_has_no_problems(self):
        self.assertEqual(change.check(NAME, minimal(), KNOWN), [])

    def test_a_proposed_change_lists_no_commits(self):
        errors = change.check(NAME, minimal(commits="3f2a9c1"), KNOWN)
        self.assertTrue(any("commit" in e for e in errors), errors)

    def test_an_implemented_change_may_list_commits(self):
        text = minimal(status="implemented", commits="3f2a9c1", decision="approved, 2026-10-26")
        self.assertEqual(change.check(NAME, text, KNOWN), [])

    def test_a_named_test_must_exist_whatever_the_status(self):
        errors = change.check(NAME, minimal(verification="CoincidenceSorter.TheWindowIs3ns."), KNOWN)
        self.assertTrue(any("TheWindowIs3ns" in e for e in errors), errors)
        ok = minimal(verification="CoincidenceSorter.TheWindowIsInclusive, and a new test.")
        self.assertEqual(change.check(NAME, ok, KNOWN), [])


class WindowChange(unittest.TestCase):
    def setUp(self):
        self.text = change.load()
        self.body = change.sections(self.text)

    def test_the_request_follows_the_rules(self):
        self.assertEqual(change.check(NAME, self.text, KNOWN), [])

    def test_it_is_proposed_not_yet_decided(self):
        fields = dict(change.FIELD_ROW.findall(self.text.split("\n## ", 1)[0]))
        self.assertEqual(fields["Status"], "proposed")

    def test_the_requirements_whose_verification_repeats(self):
        for r in ("SRS-CFG-001", "SRS-SRT-001", "SRS-SRT-011"):
            self.assertIn(r, self.body["Requirements"])

    def test_the_hazards_of_a_changed_default(self):
        for h in ("H-04", "H-07", "RC-12", "RC-16"):
            self.assertIn(h, self.body["Risk"])

    def test_old_documents_keep_their_meaning(self):
        self.assertIn("schema", self.body["Interfaces and data formats"])
        self.assertIn("1.4", self.body["Interfaces and data formats"])

    def test_the_documents_that_state_the_old_window(self):
        for d in ("minidaq/configs/default.json", "known-anomalies.md", "architecture.md"):
            self.assertIn(d, self.body["Documents"])

    def test_the_verification_names_the_tests_that_use_the_default(self):
        for t in ("CoincidenceSorter.TheWindowIsInclusive", "Config.MinimalDocumentGetsDefaults",
                  "CoincidenceSorter.TheDelayedWindowEstimateDependsOnTheMultiplesPolicy"):
            self.assertIn(t, self.body["Verification"])
        self.assertIn("measurements/ch10/validation.txt", self.body["Verification"])

    def test_the_physics_assumption_is_marked(self):
        self.assertIn("assumption: confirm", self.body["Reason"])


if __name__ == "__main__":
    unittest.main()
