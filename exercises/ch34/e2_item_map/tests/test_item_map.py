# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 34.2."""
import itertools
import unittest

from item_map import check_map, owner

ITEMS = [{"id": "config", "paths": ["src/config/", "include/config/"]},
         {"id": "hw", "paths": ["src/hw/", "src/config/hardware_config"]},
         {"id": "sorter", "paths": ["src/processing/coincidence_sorter"]},
         {"id": "processing", "paths": ["src/processing/", "src/processing/count_rates"]},
         {"id": "metrics", "paths": ["include/metrics/", "src/metrics/"]}]
FILES = ["src/config/acquisition_config.cpp", "src/config/hardware_config.cpp",
         "src/hw/slow_control.cpp", "src/processing/coincidence_sorter.cpp",
         "src/processing/sinogram.cpp", "include/metrics/latency.hpp", "tools/survey.py"]


class Owner(unittest.TestCase):
    def test_the_longest_prefix_wins_whatever_the_order(self):
        expected = {"src/config/hardware_config.cpp": "hw",
                    "src/config/acquisition_config.cpp": "config",
                    "src/processing/coincidence_sorter.cpp": "sorter",
                    "src/processing/sinogram.cpp": "processing", "tools/survey.py": None}
        for order in itertools.permutations(ITEMS):
            for f, who in expected.items():
                self.assertEqual(owner(f, list(order)), who, (f, [i["id"] for i in order]))
        reversed_prefixes = [dict(i, paths=i["paths"][::-1]) for i in ITEMS]
        self.assertEqual(owner("src/config/hardware_config.cpp", reversed_prefixes), "hw")

    def test_an_ambiguous_owner_raises_naming_both(self):
        items = ITEMS + [{"id": "audit", "paths": ["src/hw/"]}]
        with self.assertRaises(ValueError) as e:
            owner("src/hw/slow_control.cpp", items)
        self.assertIn("audit", str(e.exception))
        self.assertIn("hw", str(e.exception))

    def test_a_file_stem_claims_its_files_and_nothing_in_another_directory(self):
        items = [{"id": "x", "paths": ["src/a/x"]}]
        self.assertEqual(owner("src/a/x.cpp", items), "x")
        self.assertEqual(owner("src/a/x_test.cpp", items), "x")
        self.assertIsNone(owner("src/ab/x.cpp", items))


class CheckMap(unittest.TestCase):
    def test_unowned_shadowed_and_counts(self):
        r = check_map(FILES, ITEMS)
        self.assertEqual(r["unowned"], ["tools/survey.py"])
        self.assertEqual(r["shadowed"],
                         [("src/config/hardware_config.cpp", "hw", "config"),
                          ("src/processing/coincidence_sorter.cpp", "sorter", "processing")])
        self.assertEqual(r["owned"], {"config": 1, "hw": 2, "sorter": 1, "processing": 1,
                                      "metrics": 1})

    def test_dead_prefixes_in_the_maps_order(self):
        r = check_map(FILES, ITEMS)
        self.assertEqual(r["dead"], [("config", "include/config/"),
                                     ("processing", "src/processing/count_rates"),
                                     ("metrics", "src/metrics/")])

    def test_an_ambiguous_file_is_listed_and_nothing_raises(self):
        items = ITEMS + [{"id": "audit", "paths": ["src/hw/"]}]
        r = check_map(FILES, items)
        self.assertEqual(r["ambiguous"], ["src/hw/slow_control.cpp"])
        self.assertEqual(r["owned"]["audit"], 0)
        self.assertEqual(r["owned"]["hw"], 1)

    def test_an_item_that_owns_nothing_is_counted_as_zero(self):
        r = check_map(["src/hw/slow_control.cpp"], ITEMS)
        self.assertEqual(r["owned"]["sorter"], 0)
        self.assertEqual(r["owned"]["hw"], 1)


if __name__ == "__main__":
    unittest.main()
