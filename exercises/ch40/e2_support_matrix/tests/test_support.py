# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 40.2."""
import unittest

from support import latest, needs_plan, supported

RELEASES = [("1.2.0", "2026-11-15"), ("1.3.0", "2026-11-15"), ("1.3.1", "2027-06-01"),
            ("1.3.10", "2028-03-01"), ("1.3.2", "2027-09-01"), ("2.0.0", "2026-12-15"),
            ("1.1.0", "2026-11-10"), ("1.10.0", "2028-01-10")]


class Supported(unittest.TestCase):
    def test_a_line_is_supported_from_its_first_release(self):
        self.assertEqual(supported(RELEASES, "2026-11-12"), ["1.1"])
        self.assertEqual(supported(RELEASES, "2026-12-20"), ["1.1", "1.2", "1.3", "2.0"])

    def test_a_patch_does_not_extend_its_line(self):
        # 1.3.10 in 2028 does not keep 1.3 alive past 2028-11-15.
        self.assertIn("1.3", supported(RELEASES, "2028-11-14"))
        self.assertNotIn("1.3", supported(RELEASES, "2028-11-15"))

    def test_months_are_calendar_months(self):
        # 24 months of 30 days would end 1.1 on 2028-10-30; it ends on 2028-11-10.
        self.assertIn("1.1", supported(RELEASES, "2028-11-09"))
        self.assertNotIn("1.1", supported(RELEASES, "2028-11-10"))
        self.assertEqual(supported([("3.0.0", "2027-01-31")], "2027-02-28", months=1), [])
        self.assertEqual(supported([("3.0.0", "2027-01-31")], "2027-02-27", months=1), ["3.0"])

    def test_lines_sort_as_numbers(self):
        self.assertEqual(supported(RELEASES, "2028-02-01"), ["1.1", "1.2", "1.3", "1.10", "2.0"])

    def test_a_line_without_its_first_release_is_an_error(self):
        with self.assertRaises(ValueError):
            supported([("1.4.1", "2027-01-01")], "2027-02-01")


class Latest(unittest.TestCase):
    def test_the_newest_by_version_number(self):
        self.assertEqual(latest(RELEASES, "1.3"), "1.3.10")
        self.assertEqual(latest(RELEASES, "1.1"), "1.1.0")
        with self.assertRaises(ValueError):
            latest(RELEASES, "0.9")


class Soup(unittest.TestCase):
    def test_an_end_inside_the_period_needs_a_plan(self):
        items = {"openssl-3.0": "2026-09-07", "json": None, "lib-a": "2028-11-15",
                 "lib-b": "2028-11-16", "lib-c": "2031-01-01"}
        self.assertEqual(needs_plan(items, "2026-11-16"), ["lib-a", "openssl-3.0"])
        self.assertEqual(needs_plan(items, "2026-11-16", months=60),
                         ["lib-a", "lib-b", "lib-c", "openssl-3.0"])


if __name__ == "__main__":
    unittest.main()
