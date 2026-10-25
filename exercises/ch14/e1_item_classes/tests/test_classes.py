"""Acceptance tests for Exercise 14.1: the classification rules and MiniDAQ's classification."""
import copy
import os
import pathlib
import re
import unittest

import classes

VARIANT = pathlib.Path(classes.__file__).resolve().parent
BASE = {
    "system": {"name": "S", "class": "B"},
    "hazards": [{"id": "H1", "severity": "non-serious"}, {"id": "H2", "severity": "serious"}],
    "items": [
        {"id": "a", "runs_in": "p", "shipped": True, "class": "B", "hazards": ["H1"], "rationale": "r"},
        {"id": "b", "runs_in": "p", "shipped": True, "class": "B", "hazards": [], "rationale": "r"},
        {"id": "c", "runs_in": "q", "shipped": True, "class": "A", "hazards": [], "rationale": "r"},
        {"id": "t", "runs_in": None, "shipped": False, "class": None, "hazards": [], "rationale": "Not shipped: a tool"},
    ],
}


def variant(change):
    d = copy.deepcopy(BASE)
    change(d)
    return classes.problems(d)


def item(d, name):
    return next(i for i in d["items"] if i["id"] == name)


class Rules(unittest.TestCase):
    def test_a_consistent_document_has_no_problems(self):
        self.assertEqual(classes.problems(copy.deepcopy(BASE)), [])

    def test_the_worst_hazard_sets_the_minimum_class(self):
        def raise_harm(d):
            item(d, "a")["hazards"] = ["H1", "H2"]
        self.assertTrue(any(e.startswith("a:") and "needs C" in e for e in variant(raise_harm)))

    def test_an_unknown_hazard_is_an_error(self):
        def typo(d):
            item(d, "a")["hazards"] = ["H9"]
        self.assertTrue(any("unknown hazard H9" in e for e in variant(typo)))

    def test_items_in_one_process_share_its_highest_class(self):
        def lower(d):
            item(d, "b")["class"] = "A"
        errors = variant(lower)
        self.assertTrue(any(e.startswith("b:") and "nothing segregates" in e for e in errors), errors)

    def test_a_separate_process_may_have_a_lower_class(self):
        self.assertFalse(any(e.startswith("c:") for e in classes.problems(copy.deepcopy(BASE))))

    def test_the_system_has_the_class_of_its_highest_item(self):
        def wrong(d):
            d["system"]["class"] = "A"
        self.assertTrue(any(e.startswith("system:") for e in variant(wrong)))

    def test_a_shipped_item_needs_a_class_and_a_rationale(self):
        def none(d):
            item(d, "c")["class"] = None
        def silent(d):
            item(d, "c")["rationale"] = " "
        self.assertTrue(any(e.startswith("c:") for e in variant(none)))
        self.assertTrue(any(e.startswith("c:") for e in variant(silent)))

    def test_an_item_that_is_not_shipped_has_no_class_and_says_why(self):
        def classed(d):
            item(d, "t")["class"] = "A"
        def unexplained(d):
            item(d, "t")["rationale"] = "a tool"
        self.assertTrue(any(e.startswith("t:") for e in variant(classed)))
        self.assertTrue(any(e.startswith("t:") for e in variant(unexplained)))


class MiniDAQ(unittest.TestCase):
    def setUp(self):
        self.doc = classes.load(VARIANT / "minidaq-items.json")
        self.items = {i["id"]: i for i in self.doc["items"]}

    def test_the_classification_follows_the_rules(self):
        self.assertEqual(classes.problems(self.doc), [])

    def test_every_component_of_the_exercise_is_classified(self):
        for name in ("simulator", "sorter", "writer", "control-api", "audit-log", "client"):
            self.assertIn(name, self.items)
            self.assertTrue(self.items[name]["shipped"], f"{name} is part of the shipped software")

    def test_the_data_path_contributes_to_a_hazard(self):
        for name in ("sorter", "writer", "control-api"):
            self.assertTrue(self.items[name]["hazards"], f"{name}: which hazard can it contribute to?")
            self.assertNotEqual(self.items[name]["class"], "A", name)

    def test_every_rationale_is_an_argument(self):
        for i in self.doc["items"]:
            words = len(i["rationale"].split())
            self.assertGreaterEqual(words, 12, f"{i['id']}: say why, in a sentence or two")
            if i["shipped"] and not i["hazards"]:
                self.assertTrue(re.search(r"segregat|process", i["rationale"]),
                                f"{i['id']}: no hazard of its own; say what its class rests on")

    def test_the_client_runs_in_its_own_process(self):
        self.assertNotEqual(self.items["client"]["runs_in"], self.items["sorter"]["runs_in"])


if __name__ == "__main__":
    unittest.main()
