"""Acceptance tests for Exercise 15.1: hazard chains, their rating, and MiniDAQ's ten chains."""
import copy
import unittest

import chains

CHAIN = {"id": "C-1", "category": "data loss", "hazard": "Data lost without notice",
         "sequence": "The link drops packets; the run ends normally.",
         "hazardous_situation": "Incomplete data is reconstructed as complete.",
         "harm": "A delayed diagnosis.", "severity": "S2", "probability": "P4", "acceptable": False}


def doc(*changes):
    out = []
    for i, change in enumerate(changes):
        c = copy.deepcopy(CHAIN)
        c["id"] = f"C-{i + 1}"
        change(c)
        out.append(c)
    return {"chains": out}


def same(_):
    pass


class Rating(unittest.TestCase):
    def test_the_criterion_is_the_sum_of_the_indices(self):
        self.assertTrue(chains.acceptable("S1", "P4"))
        self.assertTrue(chains.acceptable("S2", "P3"))
        self.assertTrue(chains.acceptable("S4", "P1"))
        self.assertFalse(chains.acceptable("S2", "P4"))
        self.assertFalse(chains.acceptable("S3", "P3"))
        self.assertFalse(chains.acceptable("S1", "P5"))


class Rules(unittest.TestCase):
    def test_a_good_chain_has_no_problems(self):
        self.assertEqual(chains.problems(doc(same)), [])

    def test_an_empty_field_is_reported(self):
        def empty(c):
            c["sequence"] = "  "
        self.assertTrue(any("C-1" in e and "sequence" in e for e in chains.problems(doc(empty))))

    def test_a_duplicate_id_is_reported(self):
        d = doc(same, same)
        d["chains"][1]["id"] = "C-1"
        self.assertTrue(any("C-1" in e and "twice" in e for e in chains.problems(d)))

    def test_an_unknown_category_is_reported(self):
        def odd(c):
            c["category"] = "misc"
        self.assertTrue(any("category" in e for e in chains.problems(doc(odd))))

    def test_a_chain_that_repeats_itself_is_reported(self):
        def repeat(c):
            c["hazardous_situation"] = c["hazard"].upper()
        self.assertTrue(any("C-1" in e and "different" in e for e in chains.problems(doc(repeat))))

    def test_values_off_the_scales_are_reported(self):
        def off(c):
            c["probability"] = "P6"
        self.assertTrue(any("scale" in e for e in chains.problems(doc(off))))

    def test_a_rating_that_contradicts_the_criterion_is_reported(self):
        def wrong(c):
            c["acceptable"] = True
        self.assertTrue(any("C-1" in e and "not acceptable" in e for e in chains.problems(doc(wrong))))

    def test_the_rating_must_be_a_boolean(self):
        def text(c):
            c["acceptable"] = "no"
        self.assertTrue(chains.problems(doc(text)))


class MiniDAQ(unittest.TestCase):
    def setUp(self):
        self.doc = chains.load()

    def test_ten_chains_without_problems(self):
        self.assertGreaterEqual(len(self.doc["chains"]), 10)
        self.assertEqual(chains.problems(self.doc), [])

    def test_every_required_category_is_covered(self):
        self.assertEqual(chains.missing_categories(self.doc), [])

    def test_some_risks_need_control(self):
        self.assertTrue(any(not c["acceptable"] for c in self.doc["chains"]),
                        "rated before risk control, a DAQ has risks that are not acceptable")

    def test_sequences_say_how_it_happens(self):
        for c in self.doc["chains"]:
            self.assertGreaterEqual(len(c["sequence"].split()), 8, c["id"])


if __name__ == "__main__":
    unittest.main()
