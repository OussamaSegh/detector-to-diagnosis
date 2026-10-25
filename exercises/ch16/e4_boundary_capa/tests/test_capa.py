"""Acceptance tests for Exercise 16.4: two more CAPA rules, and a CAPA for limit values."""
import json
import pathlib
import unittest

import capa

HERE = pathlib.Path(__file__).resolve().parent
REPORTS = {r["id"]: r for r in json.loads((HERE / "problem-reports.json").read_text())["reports"]}
FILES = set((HERE / "files.txt").read_text().split())
REPO_CAPA = "CAPA-0001-timing-dependent-tests.md"
NAME = "CAPA-0003-boundary-inputs.md"


def repo_capa():
    return (HERE / REPO_CAPA).read_text()


def problems(edit):
    return capa.check(REPO_CAPA, edit(repo_capa()), REPORTS, FILES)


class Rules(unittest.TestCase):
    def test_the_repositorys_capa_passes(self):
        self.assertEqual(capa.check(REPO_CAPA, repo_capa(), REPORTS, FILES), [])

    def test_the_due_date_is_a_date_or_a_release(self):
        errors = problems(lambda t: t.replace("Due: release 0.4.0.", "Due: soon."))
        self.assertTrue(any("soon" in e for e in errors), errors)
        errors = problems(lambda t: t.replace("| Effectiveness check | release 0.4.0 |", "| Effectiveness check | later |"))
        self.assertTrue(any("later" in e for e in errors), errors)
        self.assertEqual(problems(lambda t: t.replace("Due: release 0.4.0.", "Due: 2027-03-31.")), [])

    def test_a_criterion_needs_a_number_or_a_check(self):
        def vague(t):
            start = t.index("Criterion:")
            end = t.index("Due:")
            return t[:start] + "Criterion: the tests no longer fail at random.\n" + t[end:]
        errors = problems(vague)
        self.assertTrue(any("criterion" in e for e in errors), errors)

    def test_vague_words_are_reported(self):
        def vague(t):
            start = t.index("Criterion:")
            end = t.index("Due:")
            return t[:start] + "Criterion: 100 runs show that the tests have improved.\n" + t[end:]
        errors = problems(vague)
        self.assertTrue(any("improved" in e for e in errors), errors)

    def test_the_inherited_rules_still_hold(self):
        errors = problems(lambda t: t.replace("The coding standard said nothing", "Human error: the coding standard said nothing"))
        self.assertTrue(any("blames" in e for e in errors), errors)


class BoundaryCapa(unittest.TestCase):
    def setUp(self):
        self.text = capa.load()
        self.body = capa.sections(self.text)

    def test_the_record_passes_every_rule(self):
        self.assertEqual(capa.check(NAME, self.text, REPORTS, FILES), [])

    def test_it_names_both_problem_reports(self):
        fields = dict(capa.FIELD_ROW.findall(self.text.split("\n## ", 1)[0]))
        self.assertIn("MDQ-PR-001", fields["Source"])
        self.assertIn("MDQ-PR-002", fields["Source"])

    def test_the_investigation_looked_beyond_the_two_reports(self):
        self.assertIn("fuzz/README.md", self.body["Investigation"])

    def test_the_root_cause_is_about_limits(self):
        self.assertRegex(self.body["Root cause"].lower(), r"\blimits?\b")

    def test_the_actions_change_the_standard_and_the_seeds(self):
        self.assertIn("docs/coding-standard.md", self.body["Corrective action"])
        self.assertIn("fuzz/corpus/", self.body["Preventive action"])

    def test_it_is_not_closed_before_its_check(self):
        fields = dict(capa.FIELD_ROW.findall(self.text.split("\n## ", 1)[0]))
        self.assertNotEqual(fields["Status"], "closed")


if __name__ == "__main__":
    unittest.main()
