"""Acceptance tests for Exercise 14.3: a SOUP list that matches the build."""
import pathlib
import unittest

import soup_check

HERE = pathlib.Path(__file__).resolve().parent
VARIANT = pathlib.Path(soup_check.__file__).resolve().parent
CMAKE = (HERE / "Dependencies.cmake").read_text()
SHIPPED = {"nlohmann_json"}
GTEST = "b514bdc898e2951020cbdca1304b75f5950d1f59"
JSON = "d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d"


class Pins(unittest.TestCase):
    def test_git_commits_and_archive_hashes_are_pins(self):
        p = {name: (version, pin) for name, version, pin in soup_check.pins(CMAKE)}
        self.assertEqual(p["googletest"], ("1.15.2", GTEST))
        self.assertEqual(p["googlebenchmark"], ("1.9.1", "96afad55c79e02f5dfca1374e772c2be72ba631b"))
        self.assertEqual(p["nlohmann_json"], ("3.11.3", JSON))

    def test_a_branch_is_not_a_pin(self):
        cmake = "FetchContent_Declare(foo\n  GIT_REPOSITORY https://example.org/foo.git\n  GIT_TAG main)\n"
        self.assertEqual(soup_check.pins(cmake), [("foo", None, None)])
        self.assertTrue(soup_check.check(cmake, "", "0.3.0", set()))


class Check(unittest.TestCase):
    def setUp(self):
        self.good = (VARIANT / "soup-list.md").read_text()

    def test_the_list_matches_the_build(self):
        self.assertEqual(soup_check.check(CMAKE, self.good, "0.3.0", SHIPPED), [])

    def test_a_changed_pin_is_found(self):
        self.assertTrue(any("googletest" in e for e in soup_check.check(CMAKE, self.good.replace(GTEST, GTEST[:-1] + "0"),
                                                                       "0.3.0", SHIPPED)))
        self.assertTrue(any("nlohmann_json" in e for e in soup_check.check(CMAKE, self.good.replace(JSON, "0" * 64),
                                                                          "0.3.0", SHIPPED)))

    def test_a_shipped_item_needs_every_field(self):
        for field in soup_check.FIELDS:
            lines = [ln for ln in self.good.splitlines() if not ln.startswith(f"| {field} |")]
            errors = soup_check.check(CMAKE, "\n".join(lines) + "\n", "0.3.0", SHIPPED)
            self.assertTrue(any(field in e for e in errors), field)

    def test_the_review_must_be_for_this_minor_version(self):
        self.assertTrue(any("reviewed for MiniDAQ 0.3" in e for e in soup_check.check(CMAKE, self.good, "0.4.0", SHIPPED)))
        self.assertEqual(soup_check.check(CMAKE, self.good, "0.3.7", SHIPPED), [])
        undated = self.good.replace("| Last review | 2026-10-25, for", "| Last review | recently, for")
        self.assertTrue(soup_check.check(CMAKE, undated, "0.3.0", SHIPPED))

    def test_items_used_only_for_development_need_no_review(self):
        self.assertEqual(soup_check.check(CMAKE, self.good, "0.3.0", set()), [])


if __name__ == "__main__":
    unittest.main()
