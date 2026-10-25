"""Acceptance tests for Exercise 15.5: the risk matrix and the overall residual risk."""
import copy
import json
import pathlib
import re
import unittest

import risk_matrix as rm

DOC = json.loads((pathlib.Path(__file__).resolve().parent / "hazards.json").read_text())


def closed(doc):
    d = copy.deepcopy(doc)
    for h in d["hazards"]:
        if h["status"] == "open":
            h["status"] = "closed"
            h["probability_after"] = "P2"
    return d


class Matrix(unittest.TestCase):
    def test_after_control_uses_the_residual_probability(self):
        cells = rm.matrix(DOC, "after")
        self.assertIn("H-03", cells[("S2", "P1")])
        self.assertIn("H-01", cells[("S2", "P2")])
        self.assertEqual(cells[("S2", "P4")], ["H-08"])

    def test_before_control_uses_the_initial_probability(self):
        cells = rm.matrix(DOC, "before")
        self.assertIn("H-01", cells[("S2", "P4")])
        self.assertNotIn(("S2", "P1"), cells)

    def test_every_hazard_is_in_exactly_one_cell(self):
        for when in ("before", "after"):
            ids = [i for v in rm.matrix(DOC, when).values() for i in v]
            self.assertEqual(sorted(ids), sorted(h["id"] for h in DOC["hazards"]))

    def test_the_rendered_matrix_marks_unacceptable_cells(self):
        text = rm.render(DOC)
        rows = {line.split("|")[1].strip(): line for line in text.splitlines() if re.match(r"\| S\d ", line)}
        self.assertEqual(list(rows), ["S4", "S3", "S2", "S1"])
        cells = [c.strip() for c in rows["S2"].split("|")[2:-1]]
        self.assertEqual(len(cells), 5)
        self.assertTrue(cells[3].startswith("H-08") and cells[3].endswith("*"), cells)
        self.assertFalse(cells[1].endswith("*"), "S2/P2 is acceptable")


class Overall(unittest.TestCase):
    def test_an_open_hazard_makes_the_overall_risk_unacceptable(self):
        v = rm.overall(DOC)
        self.assertFalse(v["acceptable"])
        self.assertEqual(v["open"], ["H-08"])
        self.assertTrue(any(r.startswith("H-08") for r in v["reasons"]))

    def test_closed_and_acceptable_hazards_are_acceptable(self):
        v = rm.overall(closed(DOC))
        self.assertTrue(v["acceptable"])
        self.assertEqual(v["reasons"], [])

    def test_a_closed_hazard_above_the_criterion_needs_a_justification(self):
        d = closed(DOC)
        d["hazards"][0]["probability_after"] = "P4"
        v = rm.overall(d)
        self.assertFalse(v["acceptable"])
        self.assertEqual(v["unacceptable"], [d["hazards"][0]["id"]])
        self.assertTrue(any("benefit" in r for r in v["reasons"]))


if __name__ == "__main__":
    unittest.main()
