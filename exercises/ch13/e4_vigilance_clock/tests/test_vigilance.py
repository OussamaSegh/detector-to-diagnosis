# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 13.4."""
import unittest
from datetime import date

import vigilance as v


class EU(unittest.TestCase):
    def test_three_clocks(self):
        aware = date(2027, 3, 1)
        self.assertEqual(v.eu_deadline(aware, "serious_public_health_threat"), date(2027, 3, 3))
        self.assertEqual(v.eu_deadline(aware, "death_or_unanticipated_serious_deterioration"),
                         date(2027, 3, 11))
        self.assertEqual(v.eu_deadline(aware, "serious_incident"), date(2027, 3, 16))

    def test_calendar_days_ignore_weekends_and_leap_days_count(self):
        self.assertEqual(v.eu_deadline(date(2028, 2, 20), "serious_incident"), date(2028, 3, 6))

    def test_unknown_kind_is_an_error(self):
        with self.assertRaises(KeyError):
            v.eu_deadline(date(2027, 1, 1), "minor")

    def test_psur(self):
        self.assertEqual(v.psur_interval_months("IIa"), 24)
        self.assertEqual(v.psur_interval_months("IIb"), 12)
        self.assertEqual(v.psur_interval_months("III"), 12)
        self.assertIsNone(v.psur_interval_months("I"))


class US(unittest.TestCase):
    def test_thirty_calendar_days(self):
        self.assertEqual(v.us_deadline(date(2027, 1, 15), "malfunction_or_injury_or_death"),
                         date(2027, 2, 14))

    def test_five_work_days_skip_the_weekend(self):
        # Aware on a Thursday: Fri, Mon, Tue, Wed, Thu.
        self.assertEqual(v.us_deadline(date(2027, 1, 7), "five_day"), date(2027, 1, 14))

    def test_five_work_days_skip_holidays(self):
        mlk = date(2027, 1, 18)  # Martin Luther King Jr. Day, a federal holiday
        self.assertEqual(v.us_deadline(date(2027, 1, 14), "five_day", {mlk}), date(2027, 1, 22))

    def test_unknown_kind_is_an_error(self):
        with self.assertRaises(KeyError):
            v.us_deadline(date(2027, 1, 1), "whenever")


class Plan(unittest.TestCase):
    def test_earliest_first(self):
        plan = v.report_plan(date(2027, 1, 7), "serious_incident", "five_day")
        self.assertEqual(plan, [(date(2027, 1, 14), "FDA"), (date(2027, 1, 22), "EU competent authority")])

    def test_only_what_applies(self):
        self.assertEqual(v.report_plan(date(2027, 1, 7), None, None), [])


if __name__ == "__main__":
    unittest.main()
