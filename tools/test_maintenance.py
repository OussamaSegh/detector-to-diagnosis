#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the maintenance records' tools (Chapter 40), run by CTest as tools.maintenance:
the released versions of a problem report (tools/anomalies.py), the end of support of a SOUP
item (tools/check_soup.py) and the problem report trends (tools/pr_trends.py), the last on a
small repository made for the test."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import anomalies  # noqa: E402
import check_soup  # noqa: E402
import pr_trends  # noqa: E402

CHANGELOG = """# Changelog

## [Unreleased]

## [1.1.0] - 2026-02-01

## [1.0.0] - 2026-01-01
"""


def report(rid, **extra):
    r = {"id": rid, "title": "t", "found": "2026-01-05, CI", "item": "sorter", "status": "closed",
         "description": "d", "evaluation": {"safety_relevant": False, "rationale": "r"},
         "resolution": {"change": "c", "verification": "v"}}
    r.update(extra)
    return r


class Affects(unittest.TestCase):
    releases = anomalies.released_versions(CHANGELOG)

    def test_the_released_versions_come_from_the_changelog(self):
        # REQ: SRS-MNT-001
        self.assertEqual(self.releases, ["1.0.0", "1.1.0"])

    def test_a_report_after_1_0_must_name_the_releases_it_affects(self):
        # REQ: SRS-MNT-001
        self.assertEqual(anomalies.affects_problems("MDQ-PR-064", report("MDQ-PR-064"), self.releases), [])
        self.assertTrue(anomalies.affects_problems("MDQ-PR-065", report("MDQ-PR-065"), self.releases))
        self.assertEqual(anomalies.affects_problems(
            "MDQ-PR-065", report("MDQ-PR-065", affects=[]), self.releases), [])

    def test_an_open_report_must_name_them_whatever_its_number(self):
        # REQ: SRS-MNT-001
        r = report("MDQ-PR-006", status="open", decision="keep")
        self.assertTrue(anomalies.affects_problems("MDQ-PR-006", r, self.releases))

    def test_a_version_that_was_never_released_is_refused(self):
        # REQ: SRS-MNT-001
        r = report("MDQ-PR-070", affects=["1.0.0", "1.0.1"])
        self.assertRegex(" ".join(anomalies.affects_problems("MDQ-PR-070", r, self.releases)),
                         "never released: 1.0.1")
        self.assertTrue(anomalies.affects_problems("MDQ-PR-070", report("MDQ-PR-070", affects="1.0.0"),
                                                   self.releases))

    def test_the_known_anomalies_show_the_releases(self):
        # REQ: SRS-MNT-001
        r = report("MDQ-PR-006", status="open", decision="keep",
                   affects=["0.1.0", "0.2.0", "0.3.0"])
        text = anomalies.render([r])
        self.assertIn("| In releases |", text)
        self.assertIn("| 0.1.0 to 0.3.0 (3 releases) |", text)
        self.assertEqual(anomalies.span([]), "none")
        self.assertEqual(anomalies.span(["1.3.0"]), "1.3.0")


TABLE = """| Field | lib |
|---|---|
| Identification | lib 1.0 |
| Last review | 2026-11-16, for MiniDAQ 2.0 |
"""


class SupportEnds(unittest.TestCase):
    def test_an_item_must_say_when_its_support_ends(self):
        # REQ: SRS-MNT-002
        self.assertRegex(" ".join(check_soup.support_problems("lib", TABLE)), "no '| Support ends")
        self.assertEqual(check_soup.support_problems(
            "lib", TABLE + "| Support ends | no announced end (2026-11-16) |\n"), [])
        self.assertTrue(check_soup.support_problems("lib", TABLE + "| Support ends | soon |\n"))

    def test_an_end_within_the_support_period_needs_a_plan(self):
        # REQ: SRS-MNT-002
        near = TABLE + "| Support ends | 2028-11-15 |\n"
        far = TABLE + "| Support ends | 2028-11-16 |\n"
        self.assertRegex(" ".join(check_soup.support_problems("lib", near)), "before 2028-11-16")
        self.assertEqual(check_soup.support_problems("lib", far), [])
        self.assertEqual(check_soup.support_problems(
            "lib", near + "| End-of-support plan | Move to 2.0 with CR-0099. |\n"), [])

    def test_months_are_calendar_months(self):
        # REQ: SRS-MNT-002
        self.assertEqual(check_soup.months_later("2026-11-16", 24), "2028-11-16")
        self.assertEqual(check_soup.months_later("2026-01-31", 1), "2026-02-28")
        self.assertEqual(check_soup.months_later("2026-12-01", 1), "2027-01-01")

    def test_only_the_shipped_items_are_checked(self):
        # REQ: SRS-MNT-002
        text = "## 1. Shipped\n\n" + TABLE + "\n## 2. Tools\n\n" + TABLE.replace("lib", "gtest")
        self.assertEqual(list(check_soup.shipped_tables(text)), ["lib"])


class Trends(unittest.TestCase):
    def test_the_way_a_problem_was_found(self):
        # REQ: SRS-MNT-003
        self.assertEqual(pr_trends.found_by("2026-11-15, the coverage review of release 1.3.0"),
                         "release checks")
        self.assertEqual(pr_trends.found_by("2026-11-10, the second full review (PR #9)"),
                         "review or audit")
        self.assertEqual(pr_trends.found_by("2026-10-25, GitHub CI fuzz-smoke"), "CI")
        self.assertEqual(pr_trends.found_by("2026-10-24, Chapter 7, fuzz_config"), "tests")
        self.assertEqual(pr_trends.found_by("2026-10-24, Chapter 9 measurements"), "measurement")
        self.assertEqual(pr_trends.found_by("2026-10-24, Chapter 6 design"), "development")

    def test_the_u_chart_widens_its_limit_for_a_small_window(self):
        # REQ: SRS-MNT-003
        ubar, chart = pr_trends.u_chart({"a": 10, "b": 10, "c": 0}, {"a": 100, "b": 20, "c": 0})
        self.assertAlmostEqual(ubar, 20 / 120)
        self.assertAlmostEqual(chart["a"][1], ubar + 3 * (ubar / 100) ** 0.5)
        self.assertGreater(chart["b"][0], chart["b"][1])   # 50 per 100 against about 43
        self.assertLess(chart["a"][0], chart["a"][1])
        self.assertNotIn("c", chart)                       # no exposure, no rate

    def test_a_report_counts_in_the_first_release_that_contains_its_record(self):
        # REQ: SRS-MNT-003
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)

            def git(*args):
                subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)

            git("init", "-q")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            path = root / pr_trends.REPORTS
            path.parent.mkdir(parents=True)
            (root / "CHANGELOG.md").write_text(CHANGELOG)
            reports = []
            # Two releases on one day would defeat dates; the record's commit decides.
            for rid, tag in (("MDQ-PR-001", "book-v1.0.0"), ("MDQ-PR-002", "book-v1.1.0"),
                             ("MDQ-PR-003", None)):
                reports.append(report(rid, found="2026-01-01, CI"))
                path.write_text(json.dumps({"reports": reports}, indent=2))
                git("add", "-A")
                git("commit", "-q", "-m", rid)
                if tag:
                    git("tag", tag)
            released = pr_trends.releases(CHANGELOG)
            window = pr_trends.recorded_in(root, released)
            self.assertEqual(window, {"MDQ-PR-001": "1.0.0", "MDQ-PR-002": "1.1.0",
                                      "MDQ-PR-003": "unreleased"})
            exposure = pr_trends.commits(root, released)
            self.assertEqual(exposure, {"1.0.0": 1, "1.1.0": 1, "unreleased": 1})
            reports[1]["affects"] = ["1.0.0"]
            text = pr_trends.render(*pr_trends.analyse(reports, released, exposure, window), exposure)
            self.assertIn("| 1.1.0 | 1 | 1 | 100.0 |", text)
            self.assertIn("1 recorded for 1.1.0", text)


if __name__ == "__main__":
    unittest.main()
