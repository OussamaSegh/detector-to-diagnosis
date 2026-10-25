"""Acceptance tests for Exercise 15.3: the FMEA rules and the sorter's FMEA."""
import copy
import pathlib
import unittest

import fmea

HERE = pathlib.Path(__file__).resolve().parent
REQS = fmea.requirement_ids((HERE / "sorter-requirements.md").read_text())
ROW = {"function": "energy gate", "failure_mode": "Limits handled wrongly",
       "effect": "Counts biased in every scan (H-07)", "cause": "A strict comparison",
       "severity": "S2", "detection": "Unit test on both limits", "controls": ["SRS-SRT-005"]}


def complete():
    """One row per function, two where two are required: well formed."""
    rows = []
    for f in fmea.FUNCTIONS:
        for k in range(2 if f in fmea.AT_LEAST_TWO else 1):
            r = copy.deepcopy(ROW)
            r["function"] = f
            r["failure_mode"] = f"mode {k}"
            rows.append(r)
    return {"rows": rows}


def with_row(change):
    d = complete()
    change(d["rows"][0])
    return fmea.problems(d, REQS)


class Rules(unittest.TestCase):
    def test_the_fixture_has_the_sorter_requirements(self):
        self.assertIn("SRS-SRT-009", REQS)
        self.assertNotIn("SRS-SRT-012", REQS)

    def test_a_well_formed_fmea_has_no_problems(self):
        self.assertEqual(fmea.problems(complete(), REQS), [])

    def test_an_empty_field_is_reported(self):
        def empty(r):
            r["cause"] = ""
        self.assertTrue(any("cause" in e for e in with_row(empty)))

    def test_an_unknown_function_is_reported(self):
        def other(r):
            r["function"] = "sorting"
        self.assertTrue(any("not a function" in e for e in with_row(other)))

    def test_a_missing_function_is_reported(self):
        d = complete()
        d["rows"] = [r for r in d["rows"] if r["function"] != "delayed window"]
        self.assertTrue(any("delayed window" in e for e in fmea.problems(d, REQS)))

    def test_windowing_and_order_check_need_two_failure_modes(self):
        d = complete()
        d["rows"] = [r for r in d["rows"] if not (r["function"] == "windowing" and r["failure_mode"] == "mode 1")]
        self.assertTrue(any("windowing" in e for e in fmea.problems(d, REQS)))

    def test_a_duplicate_failure_mode_is_reported(self):
        d = complete()
        d["rows"].append(copy.deepcopy(d["rows"][0]))
        self.assertTrue(any("twice" in e for e in fmea.problems(d, REQS)))

    def test_a_severity_off_the_scale_is_reported(self):
        def odd(r):
            r["severity"] = "minor"
        self.assertTrue(any("scale" in e for e in with_row(odd)))

    def test_an_effect_without_a_hazard_is_reported(self):
        def vague(r):
            r["effect"] = "Biased counts"
        self.assertTrue(any("hazard" in e for e in with_row(vague)))

    def test_a_control_that_is_not_a_requirement_is_reported(self):
        def rc(r):
            r["controls"] = ["SRS-SRT-099"]
        self.assertTrue(any("SRS-SRT-099" in e for e in with_row(rc)))

    def test_a_new_control_is_a_requirement(self):
        def short(r):
            r["controls"] = ["NEW: test the tie rule"]
        self.assertTrue(any("shall" in e for e in with_row(short)))

        def good(r):
            r["controls"] = ["NEW: The coincidence sorter shall keep the earlier of two pairs with equal energy."]
        self.assertEqual(with_row(good), [])

    def test_an_undetected_failure_needs_a_new_control(self):
        def hidden(r):
            r["detection"] = "None: nothing would notice"
        self.assertTrue(any("undetected" in e for e in with_row(hidden)))

        def proposed(r):
            r["detection"] = "None: nothing would notice"
            r["controls"] = ["SRS-SRT-005", "NEW: The coincidence sorter shall count every single it drops by energy."]
        self.assertEqual(with_row(proposed), [])


class SorterFmea(unittest.TestCase):
    def setUp(self):
        self.doc = fmea.load()

    def test_the_sorters_fmea_is_well_formed(self):
        self.assertEqual(fmea.problems(self.doc, REQS), [])

    def test_it_is_more_than_a_row_per_function(self):
        self.assertGreaterEqual(len(self.doc["rows"]), 12)

    def test_it_finds_at_least_one_gap(self):
        self.assertTrue(any(c.startswith("NEW:") for r in self.doc["rows"] for c in r["controls"]),
                        "an FMEA of real code that proposes nothing new was not done against the code")

    def test_the_accounting_identity_is_a_control(self):
        self.assertTrue(any("SRS-SRT-009" in r["controls"] for r in self.doc["rows"]))


if __name__ == "__main__":
    unittest.main()
