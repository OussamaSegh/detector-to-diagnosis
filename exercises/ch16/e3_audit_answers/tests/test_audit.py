"""Acceptance tests for Exercise 16.3: the audit answer rules, and the answers about the sorter."""
import json
import pathlib
import unittest

import audit

HERE = pathlib.Path(__file__).resolve().parent
QUESTIONS = json.loads((HERE / "questions.json").read_text())["questions"]
FILES = set((HERE / "files.txt").read_text().split())
TESTS = set((HERE / "tests.txt").read_text().split())
GOOD = {q["id"]: {"answer": "Twelve requirements.", "evidence": ["docs/regulatory/srs.md"]} for q in QUESTIONS}


def problems(qid, answer=None, evidence=None):
    a = json.loads(json.dumps(GOOD))
    if answer is not None:
        a[qid]["answer"] = answer
    if evidence is not None:
        a[qid]["evidence"] = evidence
    return audit.problems(a, QUESTIONS, FILES, TESTS)


class Rules(unittest.TestCase):
    def test_good_answers_have_no_problems(self):
        self.assertEqual(audit.problems(GOOD, QUESTIONS, FILES, TESTS), [])

    def test_an_unanswered_question_is_reported(self):
        a = dict(GOOD)
        del a["Q5"]
        self.assertTrue(any(e.startswith("Q5") for e in audit.problems(a, QUESTIONS, FILES, TESTS)))

    def test_hedges_are_reported(self):
        for hedge in ("It should be fine.", "Probably B.", "I think so.", "Maybe twelve."):
            self.assertTrue(problems("Q2", answer=hedge), hedge)

    def test_a_hedge_is_a_whole_word(self):
        self.assertEqual(problems("Q2", answer="Shoulder-to-shoulder reviews."), [])

    def test_a_long_answer_is_reported(self):
        self.assertTrue(problems("Q2", answer="word " * (audit.MAX_WORDS + 1)))

    def test_evidence_must_exist(self):
        self.assertTrue(any("risk-analysis.md" in e
                            for e in problems("Q4", evidence=["docs/regulatory/risk-analysis.md"])))
        self.assertTrue(problems("Q2", evidence=["CoincidenceSorter.IsCorrect"]))
        self.assertEqual(problems("Q2", evidence=["CoincidenceSorter.TheWindowIsInclusive"]), [])

    def test_an_answer_needs_evidence(self):
        self.assertTrue(problems("Q3", evidence=[]))

    def test_a_directory_alone_is_not_evidence(self):
        self.assertTrue(problems("Q2", evidence=["minidaq/tests/"]))
        self.assertEqual(problems("Q2", evidence=["minidaq/tests/", "docs/regulatory/trace-matrix.md"]), [])


class Sorter(unittest.TestCase):
    def setUp(self):
        self.a = audit.load()

    def test_the_answers_have_no_problems(self):
        self.assertEqual(audit.problems(self.a, QUESTIONS, FILES, TESTS), [])

    def test_correctness_rests_on_the_ground_truth(self):
        self.assertIn("CoincidenceSorter.MatchesTheSimulatorsGroundTruth", self.a["Q2"]["evidence"])

    def test_the_risk_analysis_names_the_sorters_hazard_and_fmea(self):
        self.assertIn("H-07", self.a["Q4"]["answer"])
        self.assertIn("docs/regulatory/risk/fmea-sorter.json", self.a["Q4"]["evidence"])

    def test_the_design_decision_is_the_adr(self):
        self.assertTrue(any(e.startswith("docs/adr/0010") for e in self.a["Q5"]["evidence"]))

    def test_the_known_anomaly_is_named(self):
        self.assertIn("MDQ-PR-007", self.a["Q8"]["answer"])

    def test_the_missing_review_is_admitted(self):
        self.assertIn("nonconformity", self.a["Q9"]["answer"])
        self.assertIn("docs/regulatory/sdp.md", self.a["Q9"]["evidence"])


if __name__ == "__main__":
    unittest.main()
