# SPDX-License-Identifier: MIT
"""Exercise 33.5 (A): tests of the agent's count checks: the partition with every counter in
it and each off by one, and the singles at the end of a run."""
import unittest

GOOD = {"singles_in": 20, "energy_rejected": 3, "alone": 4, "pairs": 4, "in_multiples": 3,
        "out_of_order": 2}


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def test_a_partition_that_adds_up_has_no_problem(self):
        self.assertEqual(self.subject.partition_problems(GOOD), [])

    def test_a_run_with_out_of_order_singles_adds_up(self):
        c = dict(GOOD, singles_in=25, out_of_order=7)
        self.assertEqual(self.subject.partition_problems(c), [])

    def test_every_counter_off_by_one_is_a_problem(self):
        for name in GOOD:
            for delta in (-1, 1):
                with self.subTest(counter=name, delta=delta):
                    self.assertTrue(self.subject.partition_problems(dict(GOOD, **{name: GOOD[name] + delta})))

    def test_singles_before_the_end_are_recorded(self):
        self.assertEqual(self.subject.recorded_singles([0, 10, 999], 1_000), 3)

    def test_the_single_the_simulator_generated_at_or_past_the_end_is_not_recorded(self):
        self.assertEqual(self.subject.recorded_singles([0, 10, 999, 1_000], 1_000), 3)
        self.assertEqual(self.subject.recorded_singles([0, 10, 1_004], 1_000), 2)

    def test_recorded_singles_match_what_the_sender_sent(self):
        # The reference sends every single before the end: one count, two ways (system.e2e).
        generated = list(range(0, 5_000_001, 7))
        sent = [t for t in generated if t < 5_000_000]
        self.assertEqual(self.subject.recorded_singles(generated, 5_000_000), len(sent))
