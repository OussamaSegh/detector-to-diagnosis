# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 19.1. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this).

recorded.json holds four real runs of minidaq_send into minidaq_server, as the system tests
of Chapter 19 make them: what the sender reported, and the server's link counters at the end."""
import copy
import json
import pathlib
import unittest

import accounting

RECORDED = json.loads((pathlib.Path(__file__).parent / "recorded.json").read_text())


def corrupt(case, **changes):
    run = copy.deepcopy(RECORDED[case])
    for key, delta in changes.items():
        run["link"][key] += delta
    return accounting.check(run["sent"], run["link"])


class RecordedRuns(unittest.TestCase):
    def test_every_recorded_run_is_accounted_for(self):
        for name, run in RECORDED.items():
            self.assertEqual(accounting.check(run["sent"], run["link"]), [], name)

    def test_the_recordings_contain_packets_that_came_too_late(self):
        # Otherwise the identities for lost and stale could ignore late packets and still pass.
        run = RECORDED["damaged_heavy"]
        sent = run["sent"]
        self.assertGreater(sent["delayed"] - sent["both"] - run["link"]["packets_reordered"], 0)

    def test_the_recordings_contain_packets_both_delayed_and_duplicated(self):
        self.assertGreater(RECORDED["damaged_heavy"]["sent"]["both"], 0)


class EachIdentity(unittest.TestCase):
    def test_a_reordered_packet_that_was_never_delayed(self):
        delayed = RECORDED["damaged"]["sent"]["delayed"]
        reordered = RECORDED["damaged"]["link"]["packets_reordered"]
        self.assertIn("reordered", corrupt("damaged", packets_reordered=delayed - reordered + 1))

    def test_a_sequence_number_counted_twice(self):
        self.assertIn("sequence", corrupt("damaged", packets_delivered=1))

    def test_a_loss_not_counted(self):
        self.assertIn("lost", corrupt("damaged", packets_lost=-1, packets_delivered=1))

    def test_a_late_packet_counted_as_reordered_and_stale(self):
        # Moves one packet from "too late" to "reordered" without changing what was lost.
        self.assertIn("stale", corrupt("damaged_heavy", packets_reordered=1, packets_lost=1,
                                       packets_delivered=-1))

    def test_a_late_duplicate_counted_as_a_late_packet(self):
        # As if the late original of a delayed and duplicated packet had made a loss.
        self.assertIn("lost", corrupt("damaged_heavy", packets_lost=1, packets_delivered=-1))

    def test_a_stale_packet_not_counted(self):
        self.assertIn("stale", corrupt("damaged", packets_stale=-1, packets_received=-1))

    def test_a_received_packet_that_went_nowhere(self):
        self.assertIn("received", corrupt("damaged", packets_received=1))

    def test_a_datagram_lost_on_the_way(self):
        self.assertIn("datagrams", corrupt("clean", datagrams=-1))

    def test_a_single_lost_inside_a_packet(self):
        self.assertIn("words", corrupt("clean", words_delivered=-1))

    def test_a_resync(self):
        self.assertIn("resyncs", corrupt("wrap", sequence_resyncs=1))

    def test_a_correct_run_names_nothing(self):
        self.assertEqual(corrupt("damaged"), [])


if __name__ == "__main__":
    unittest.main()
