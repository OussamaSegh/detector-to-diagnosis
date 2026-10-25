"""Acceptance tests for Exercise 16.1: the clause map's rules and MiniDAQ's mapping."""
import copy
import json
import pathlib
import unittest

import clause_map

HERE = pathlib.Path(__file__).resolve().parent
CLAUSES = json.loads((HERE / "clauses.json").read_text())["clauses"]
DOCUMENTS = [d for d in (HERE / "documents.txt").read_text().splitlines() if d]
GOOD = {"clauses": {c: {"evidence": [DOCUMENTS[0]]} for c in clause_map.DESIGN}}
GOOD["clauses"]["7.3.7"] = {"evidence": [], "plan": "System validation with phantoms."}
GOOD["clauses"]["7.3.6"] = {"evidence": DOCUMENTS[1:]}


def problems(change):
    m = copy.deepcopy(GOOD)
    change(m["clauses"])
    return clause_map.problems(m, CLAUSES, DOCUMENTS)


class Rules(unittest.TestCase):
    def test_a_complete_mapping_has_no_problems(self):
        self.assertEqual(clause_map.problems(copy.deepcopy(GOOD), CLAUSES, DOCUMENTS), [])

    def test_an_unknown_clause_is_reported(self):
        def add(c):
            c["7.3.11"] = {"evidence": [DOCUMENTS[0]]}
        self.assertTrue(any("7.3.11" in e for e in problems(add)))

    def test_an_unknown_document_is_reported(self):
        def add(c):
            c["7.3.4"]["evidence"].append("docs/design.docx")
        self.assertTrue(any("design.docx" in e for e in problems(add)))

    def test_a_missing_design_clause_is_reported(self):
        def drop(c):
            del c["7.3.9"]
        self.assertTrue(any(e.startswith("7.3.9") for e in problems(drop)))

    def test_a_design_clause_needs_evidence_or_a_plan(self):
        def empty(c):
            c["7.3.8"] = {"evidence": []}
        self.assertTrue(any(e.startswith("7.3.8") for e in problems(empty)))

    def test_an_unused_document_is_reported(self):
        def drop(c):
            c["7.3.6"]["evidence"].remove("CHANGELOG.md")
        self.assertTrue(any("CHANGELOG.md" in e for e in problems(drop)))

    def test_verification_is_not_validation(self):
        def confuse(c):
            c["7.3.7"]["evidence"] = ["minidaq/tests/"]
        self.assertTrue(any("7.3.7" in e and "verification" in e for e in problems(confuse)))


class MiniDAQ(unittest.TestCase):
    def setUp(self):
        self.m = clause_map.load()

    def test_the_mapping_has_no_problems(self):
        self.assertEqual(clause_map.problems(self.m, CLAUSES, DOCUMENTS), [])

    def test_the_key_documents_are_where_an_auditor_looks(self):
        c = self.m["clauses"]
        self.assertIn("docs/regulatory/srs.md", c["7.3.3"]["evidence"])
        self.assertIn("docs/regulatory/trace-matrix.md", c["7.3.6"]["evidence"])
        self.assertIn("docs/regulatory/soup-list.md", c["7.4"]["evidence"])
        self.assertTrue(any("risk" in d for d in c["7.1"]["evidence"]))

    def test_validation_is_planned_not_claimed(self):
        self.assertEqual(self.m["clauses"]["7.3.7"].get("evidence", []), [])
        self.assertGreaterEqual(len(self.m["clauses"]["7.3.7"].get("plan", "").split()), 8)


if __name__ == "__main__":
    unittest.main()
