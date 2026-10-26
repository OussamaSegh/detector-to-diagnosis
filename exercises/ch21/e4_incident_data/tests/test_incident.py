# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 21.4. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import unittest

import incident as inc
from pipeline_sim import STAGES, simulate


def snapshot_time(snaps, sec):
    """The t_s of the snapshot taken at the end of second `sec` (0-based) of the simulation."""
    return snaps[sec]["t_s"]


class Rates(unittest.TestCase):
    def test_a_steady_run_has_the_offered_rate(self):
        snaps = simulate(seconds=20)
        r = inc.rates(snaps, "decode")
        self.assertEqual(len(r), 19)
        for _, v in r:
            self.assertAlmostEqual(v, 1000, delta=60)

    def test_a_restart_leaves_one_interval_out(self):
        snaps = simulate(seconds=20, restart_at=9)
        self.assertEqual(len(inc.rates(snaps, "write")), 18)

    def test_a_missed_snapshot_is_divided_by_the_real_time(self):
        snaps = simulate(seconds=20, missing={10})
        r = dict(inc.rates(snaps, "pair"))
        self.assertAlmostEqual(r[snaps[10]["t_s"]], 1000, delta=60, msg="two seconds, not one")


class Incident(unittest.TestCase):
    def test_a_steady_run_has_no_onset(self):
        snaps = simulate(seconds=60)
        self.assertIsNone(inc.first_to_slow(snaps))
        self.assertIsNone(inc.loss_began(snaps))

    def test_the_slow_stage_is_found_for_every_stage(self):
        for slow in STAGES[1:]:
            with self.subTest(slow=slow):
                snaps = simulate(seconds=60, slow=slow, at_s=30, seed=STAGES.index(slow))
                stage, t = inc.first_to_slow(snaps)
                self.assertEqual(stage, slow)
                self.assertEqual(t, snapshot_time(snaps, 30))

    def test_with_coarse_polling_the_starved_stage_is_not_blamed(self):
        # A snapshot every two seconds: the slow stage and the stage after it, which it starves,
        # slow in the same interval. The cause is the one upstream.
        for slow in ("decode", "sort"):  # not pair: the writer's baseline holds the start-up
            with self.subTest(slow=slow):
                snaps = simulate(seconds=60, slow=slow, at_s=30)[::2]
                after = STAGES[STAGES.index(slow) + 1]
                self.assertEqual(inc.onset(snaps, slow), inc.onset(snaps, after), "same interval")
                self.assertEqual(inc.first_to_slow(snaps)[0], slow)

    def test_the_stages_before_it_slow_later_in_order(self):
        snaps = simulate(seconds=90, slow="write", at_s=30)
        times = [inc.onset(snaps, s) for s in STAGES]
        self.assertTrue(all(t is not None for t in times), times)
        self.assertEqual(times, sorted(times, reverse=True), "write first, then pair, ..., source")
        self.assertGreater(times[0], times[-1], "the source slows only when every queue is full")

    def test_loss_begins_only_when_the_queues_are_full(self):
        # The queues hold the backlog for a while: data is lost about 20 s after the stage slowed,
        # which is the time an operator had to act.
        snaps = simulate(seconds=90, slow="write", at_s=30)
        lost = inc.loss_began(snaps)
        self.assertIsNotNone(lost)
        self.assertGreater(lost, inc.onset(snaps, "write") + 15)
        self.assertGreater(lost, inc.onset(snaps, "sort"))

    def test_the_answer_survives_a_restart_and_a_missed_snapshot(self):
        snaps = simulate(seconds=60, slow="sort", at_s=30, restart_at=5, missing={20})
        stage, t = inc.first_to_slow(snaps)
        self.assertEqual(stage, "sort")
        self.assertEqual(t, snaps[29]["t_s"], "one snapshot fewer before it")


if __name__ == "__main__":
    unittest.main()
