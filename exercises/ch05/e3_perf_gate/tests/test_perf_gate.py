# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 5.3. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import json
import math
import os
import tempfile
import unittest

import perf_gate as g


def bench_json(rows):
    """rows: list of (name, [values]) with items_per_second, or (name, [values], 'time')."""
    out = []
    for row in rows:
        name, values = row[0], row[1]
        timed = len(row) > 2
        for i, v in enumerate(values):
            b = {"name": f"{name}", "run_name": name, "run_type": "iteration", "repetition_index": i,
                 "real_time": v if timed else 1.0, "cpu_time": 1.0, "time_unit": "ns"}
            if not timed:
                b["items_per_second"] = v
            out.append(b)
        out.append({"name": f"{name}_median", "run_name": name, "run_type": "aggregate",
                    "aggregate_name": "median", "real_time": 0.0, "items_per_second": 0.0})
    return {"context": {}, "benchmarks": out}


class TempJson:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(self.data, f)
        return self.path

    def __exit__(self, *exc):
        os.unlink(self.path)


BASE = [100.0, 101.0, 99.0, 100.5, 99.5, 100.2, 99.8]


class Load(unittest.TestCase):
    def test_repetitions_only_and_metric(self):
        with TempJson(bench_json([("BM_A", [1.0, 2.0, 3.0]), ("BM_T", [5.0, 6.0], "time")])) as p:
            d = g.load(p)
        self.assertEqual(d["BM_A"].values, [1.0, 2.0, 3.0])  # the aggregate row is ignored
        self.assertTrue(d["BM_A"].higher_is_better)
        self.assertEqual(d["BM_T"].values, [5.0, 6.0])
        self.assertFalse(d["BM_T"].higher_is_better)


class MannWhitney(unittest.TestCase):
    def test_exact_values(self):
        self.assertAlmostEqual(g.mann_whitney_p_less([1, 2, 3], [4, 5, 6]), 1 / 20)
        self.assertAlmostEqual(g.mann_whitney_p_less([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]), 1 / 252)
        self.assertAlmostEqual(g.mann_whitney_p_less([4, 5, 6], [1, 2, 3]), 1.0)

    def test_interleaved_is_not_significant(self):
        self.assertGreater(g.mann_whitney_p_less([1, 3, 5, 7, 9], [2, 4, 6, 8, 10]), 0.2)


class Compare(unittest.TestCase):
    def verdict(self, base_rows, cur_rows, **kw):
        with TempJson(bench_json(base_rows)) as b, TempJson(bench_json(cur_rows)) as c:
            return {v.name: v for v in g.compare(g.load(b), g.load(c), **kw)}

    def test_clear_ten_percent_regression_fails(self):
        v = self.verdict([("BM_A", BASE)], [("BM_A", [x * 0.9 for x in BASE])])["BM_A"]
        self.assertTrue(v.regressed)
        self.assertAlmostEqual(v.ratio, 0.9, places=3)

    def test_small_slowdown_within_threshold_passes(self):
        v = self.verdict([("BM_A", BASE)], [("BM_A", [x * 0.97 for x in BASE])])["BM_A"]
        self.assertFalse(v.regressed)

    def test_noisy_slowdown_is_not_significant(self):
        noisy_base = [60.0, 140.0, 70.0, 130.0, 100.0, 125.0, 75.0]
        noisy_cur = [55.0, 135.0, 65.0, 120.0, 90.0, 118.0, 70.0]  # median 10% lower, but overlapping
        v = self.verdict([("BM_A", noisy_base)], [("BM_A", noisy_cur)])["BM_A"]
        self.assertLess(v.ratio, 0.95)
        self.assertFalse(v.regressed)

    def test_faster_passes(self):
        v = self.verdict([("BM_A", BASE)], [("BM_A", [x * 1.3 for x in BASE])])["BM_A"]
        self.assertFalse(v.regressed)
        self.assertGreater(v.ratio, 1.25)

    def test_time_metric_lower_is_better(self):
        v = self.verdict([("BM_T", BASE, "time")], [("BM_T", [x * 1.2 for x in BASE], "time")])["BM_T"]
        self.assertTrue(v.regressed)
        self.assertAlmostEqual(v.ratio, 1 / 1.2, places=3)

    def test_missing_and_too_few_repetitions_are_reported_not_failed(self):
        d = self.verdict([("BM_A", BASE), ("BM_B", BASE[:3])], [("BM_B", [x * 0.5 for x in BASE[:3]])])
        self.assertFalse(d["BM_A"].regressed)
        self.assertIn("missing", d["BM_A"].note)
        self.assertFalse(d["BM_B"].regressed)
        self.assertIn("5", d["BM_B"].note)
        self.assertTrue(math.isnan(d["BM_A"].ratio))


class Main(unittest.TestCase):
    def test_exit_status(self):
        with TempJson(bench_json([("BM_A", BASE)])) as b:
            with TempJson(bench_json([("BM_A", [x * 0.8 for x in BASE])])) as bad:
                self.assertEqual(g.main([b, bad]), 1)
            with TempJson(bench_json([("BM_A", BASE)])) as same:
                self.assertEqual(g.main([b, same]), 0)
            with TempJson(bench_json([])) as empty:
                self.assertEqual(g.main([b, empty]), 0)
                self.assertEqual(g.main([b, empty, "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
