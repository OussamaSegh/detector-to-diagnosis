# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 33.3."""
import unittest

from freeze import differences, digests, unexplained

SRS = """# Software requirements

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SYS-001 | The server shall write every coincidence it sorts. | output | T |
| SRS-SYS-002 | When the link loses a packet, the server shall mark the run incomplete. | readout | T |
| SRS-PERF-020 | The pipeline shall sort at least 20 M singles/s. | pipeline | M |

SRS-SYS-001 is checked by the system tests.
"""


class Digests(unittest.TestCase):
    def test_every_requirement_row_and_nothing_else(self):
        self.assertEqual(sorted(digests(SRS)), ["SRS-PERF-020", "SRS-SYS-001", "SRS-SYS-002"])

    def test_spaces_inside_a_cell_change_nothing(self):
        rewrapped = SRS.replace("shall write every", "shall  write\tevery")
        self.assertEqual(digests(rewrapped), digests(SRS))

    def test_padding_of_the_cells_changes_nothing(self):
        padded = SRS.replace("| output | T |", "|   output   |  T  |")
        self.assertEqual(digests(padded), digests(SRS))

    def test_a_word_of_the_text_item_or_method_changes_the_digest(self):
        base = digests(SRS)
        for old, new in (("20 M", "15 M"), ("| pipeline |", "| sorter |"), ("| M |", "| T |")):
            with self.subTest(new):
                self.assertNotEqual(digests(SRS.replace(old, new))["SRS-PERF-020"],
                                    base["SRS-PERF-020"])


class Differences(unittest.TestCase):
    def test_added_changed_and_removed_sorted_by_id(self):
        base = digests(SRS)
        now = SRS.replace("20 M", "15 M").replace(
            "| SRS-SYS-002 |", "| SRS-SYS-009 |")  # SYS-002 renumbered: one removed, one added
        self.assertEqual(differences(base, digests(now)),
                         [("SRS-PERF-020", "changed"), ("SRS-SYS-002", "removed"),
                          ("SRS-SYS-009", "added")])

    def test_an_unchanged_srs_has_no_difference(self):
        self.assertEqual(differences(digests(SRS), digests(SRS)), [])


class Unexplained(unittest.TestCase):
    def setUp(self):
        self.base = digests(SRS)
        self.now = SRS.replace("20 M", "15 M").replace(
            "| SRS-SYS-002 | When the link loses a packet, the server shall mark the run incomplete. "
            "| readout | T |\n", "")

    def test_a_change_no_request_names_is_reported(self):
        self.assertEqual(unexplained(self.base, self.now, []),
                         [("SRS-PERF-020", "changed"), ("SRS-SYS-002", "removed")])

    def test_only_an_approved_or_implemented_request_names_a_change(self):
        for status, expected in (("proposed", 2), ("rejected", 2), ("approved", 0),
                                 ("implemented", 0)):
            with self.subTest(status):
                cr = {"name": "CR-0099", "status": status,
                      "text": "Lower SRS-PERF-020 to 15 M and withdraw SRS-SYS-002."}
                self.assertEqual(len(unexplained(self.base, self.now, [cr])), expected)

    def test_each_request_names_only_what_it_mentions(self):
        crs = [{"name": "CR-0098", "status": "approved", "text": "SRS-PERF-020: 15 M."},
               {"name": "CR-0099", "status": "proposed", "text": "Withdraw SRS-SYS-002."}]
        self.assertEqual(unexplained(self.base, self.now, crs), [("SRS-SYS-002", "removed")])


if __name__ == "__main__":
    unittest.main()
