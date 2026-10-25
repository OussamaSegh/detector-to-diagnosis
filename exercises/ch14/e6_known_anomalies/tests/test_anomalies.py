"""Acceptance tests for Exercise 14.6: the known anomalies of a release."""
import copy
import unittest

import anomalies

OPEN = {"id": "MDQ-PR-007", "title": "Sorter holds its last singles", "found": "Chapter 10", "item": "sorter",
        "status": "open", "description": "d",
        "evaluation": {"safety_relevant": False, "rationale": "Processed at the end of the run."},
        "decision": "Release with it."}
OPEN_SAFETY = {"id": "MDQ-PR-006", "title": "Faults noticed 20 ms late", "found": "Chapter 6", "item": "service",
               "status": "open", "description": "d",
               "evaluation": {"safety_relevant": True, "rationale": "The run ends in a fault anyway."},
               "decision": "Chapter 15 decides."}
CLOSED = {"id": "MDQ-PR-001", "title": "Overflow crashed the reader", "found": "Chapter 7", "item": "config",
          "status": "closed", "description": "d",
          "evaluation": {"safety_relevant": True, "rationale": "A lost scan."},
          "resolution": {"change": "Catch json::exception.", "verification": "Config.NumberOverflowIsAnErrorNotACrash"}}
REPORTS = [OPEN, CLOSED, OPEN_SAFETY]


def changed(report, **kw):
    r = copy.deepcopy(report)
    r.update(kw)
    return r


class Problems(unittest.TestCase):
    def test_complete_reports_have_no_problems(self):
        self.assertEqual(anomalies.problems(REPORTS), [])

    def test_every_report_is_evaluated_for_safety(self):
        for ev in ({}, {"safety_relevant": "maybe", "rationale": "r"}, {"safety_relevant": False, "rationale": " "}):
            self.assertTrue(anomalies.problems([changed(CLOSED, evaluation=ev)]), ev)
            self.assertTrue(anomalies.problems([changed(OPEN, evaluation=ev)]), ev)

    def test_an_open_report_records_its_decision(self):
        r = copy.deepcopy(OPEN)
        del r["decision"]
        self.assertTrue(any("decision" in e for e in anomalies.problems([r])))

    def test_a_closed_report_names_change_and_verification(self):
        self.assertTrue(anomalies.problems([changed(CLOSED, resolution={"change": "Fixed."})]))

    def test_ids_are_unique_and_well_formed(self):
        self.assertTrue(anomalies.problems([OPEN, changed(OPEN_SAFETY, id="MDQ-PR-007")]))
        self.assertTrue(anomalies.problems([changed(OPEN, id="BUG-7")]))


class KnownAnomalies(unittest.TestCase):
    def setUp(self):
        self.text = anomalies.render(REPORTS)
        self.rows = [ln for ln in self.text.splitlines() if ln.startswith("| MDQ-PR-")]

    def test_only_open_reports_are_listed_in_id_order(self):
        self.assertEqual([r.split("|")[1].strip() for r in self.rows], ["MDQ-PR-006", "MDQ-PR-007"])

    def test_each_row_states_relevance_reason_and_decision(self):
        self.assertIn("| yes | The run ends in a fault anyway. | Chapter 15 decides. |", self.rows[0])
        self.assertIn("| no |", self.rows[1])

    def test_the_summary_counts_the_safety_relevant_ones(self):
        self.assertIn("2 open problem reports, 1 of them relevant to safety.", self.text)


if __name__ == "__main__":
    unittest.main()
