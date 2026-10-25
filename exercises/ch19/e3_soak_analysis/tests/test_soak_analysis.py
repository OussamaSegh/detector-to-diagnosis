# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 19.3. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import csv
import os
import random
import tempfile
import unittest

import soak_analysis as sa

RATE = 1_000_000


def run(minutes=30, interval=10, rss_mib=30.0, noise_kib=64, leak_mib_h=0.0, leak_until_s=None,
        p99_ms=2.0, p99_noise=0.1, latency_ms_h=0.0, seed=1):
    """Synthetic samples of a soak run, as tools/soak.py records them."""
    rnd = random.Random(seed)
    rows = []
    for i in range(int(minutes * 60 / interval) + 1):
        t = i * interval
        grow_t = t if leak_until_s is None else min(t, leak_until_s)
        rows.append({"t_s": float(t),
                     "rss_kib": int(rss_mib * 1024 + leak_mib_h * 1024 * grow_t / 3600 + rnd.gauss(0, noise_kib)),
                     "singles_in": int(RATE * t + rnd.randint(0, 1000)), "losses": 0, "state": "running",
                     "fault": "", "p99_ms": max(0.0, p99_ms + latency_ms_h * t / 3600 + rnd.gauss(0, p99_noise)),
                     "max_ms": 5.0})
    return rows


def kinds(rows, **kw):
    return sorted({k for k, _ in sa.analyze(rows, **kw)})


class Verdicts(unittest.TestCase):
    def test_a_steady_run_passes(self):
        for seed in range(5):
            self.assertEqual(sa.analyze(run(seed=seed)), [], f"seed {seed}")

    def test_a_slow_leak_is_found(self):
        self.assertEqual(kinds(run(leak_mib_h=3.0)), ["memory"])

    def test_growth_during_the_warm_up_does_not_count(self):
        # 40 MiB/h for the first 8 minutes (pools filling), flat afterward.
        self.assertEqual(kinds(run(leak_mib_h=40.0, leak_until_s=480)), [])

    def test_noise_alone_is_not_a_leak(self):
        # Half a MiB of noise per sample: the slope wanders, its standard error says by how much.
        for seed in range(10):
            self.assertNotIn("memory", kinds(run(noise_kib=512, seed=seed)), f"seed {seed}")

    def test_the_limit_is_a_parameter(self):
        rows = run(leak_mib_h=3.0)
        self.assertEqual(kinds(rows, max_growth_mib_h=10.0), [])

    def test_a_latency_drift_is_found(self):
        self.assertEqual(kinds(run(latency_ms_h=6.0)), ["latency"])

    def test_a_counter_that_wraps_is_found(self):
        rows = run()
        for r in rows[100:]:
            r["singles_in"] -= 2**32  # a 32-bit counter somewhere on the way wrapped
        self.assertIn("counter", kinds(rows))

    def test_a_stall_is_found(self):
        rows = run()
        step = rows[90]["singles_in"] - rows[89]["singles_in"]
        for r in rows[90:]:
            r["singles_in"] -= step  # one interval without progress
        self.assertEqual(kinds(rows), ["stall"])

    def test_a_loss_is_found(self):
        rows = run()
        for r in rows[150:]:
            r["losses"] = 17
        self.assertEqual(kinds(rows), ["loss"])

    def test_a_fault_is_found(self):
        rows = run()
        rows[120]["fault"] = "detector: read failed"
        self.assertIn("fault", kinds(rows))
        rows = run()
        rows[60]["state"] = "fault"
        self.assertIn("fault", kinds(rows))

    def test_a_run_shorter_than_the_warm_up_cannot_pass(self):
        self.assertEqual(kinds(run(minutes=5)), ["short"])

    def test_every_problem_has_a_detail(self):
        rows = run(leak_mib_h=3.0, latency_ms_h=6.0)
        rows[-1]["losses"] = 1
        for kind, detail in sa.analyze(rows):
            self.assertIsInstance(detail, str)
            self.assertTrue(detail, kind)


class Csv(unittest.TestCase):
    def test_samples_from_soak_py_load_with_their_types(self):
        rows = run(minutes=12)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "samples.csv")
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            loaded = sa.load_csv(path)
        self.assertEqual(len(loaded), len(rows))
        self.assertIsInstance(loaded[3]["rss_kib"], int)
        self.assertIsInstance(loaded[3]["t_s"], float)
        self.assertEqual(loaded[3]["state"], "running")
        self.assertEqual(sa.analyze(loaded), [])


if __name__ == "__main__":
    unittest.main()
