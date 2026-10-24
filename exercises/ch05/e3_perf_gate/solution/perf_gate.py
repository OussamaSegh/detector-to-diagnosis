#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Performance regression gate for Google Benchmark results (Chapter 5).

Compares a current run against a baseline, both produced with
  --benchmark_repetitions=N --benchmark_format=json   (N >= 5)
and fails (exit status 1) if any benchmark got slower by more than the
threshold *and* the difference is statistically significant, so that noise
alone does not fail the build and a real regression does.

  perf_gate.py baseline.json current.json [--threshold 0.05] [--alpha 0.01]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from math import comb


@dataclass
class Samples:
    values: list[float]  # one value per repetition
    higher_is_better: bool  # throughput (items/s) or time (lower is better)
    unit: str


def load(path: str) -> dict[str, Samples]:
    """Per-repetition samples by benchmark name; aggregates are ignored."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, Samples] = {}
    for b in data.get("benchmarks", []):
        if b.get("run_type", "iteration") != "iteration" or b.get("error_occurred"):
            continue
        name = b.get("run_name", b["name"])
        if "items_per_second" in b:
            value, better, unit = float(b["items_per_second"]), True, "items/s"
        else:
            value, better, unit = float(b["real_time"]), False, b.get("time_unit", "ns")
        s = out.setdefault(name, Samples([], better, unit))
        s.values.append(value)
    return out


# [snippet:mannwhitney]
def mann_whitney_p_less(a: list[float], b: list[float]) -> float:
    """One-sided exact p-value that values in `a` tend to be smaller than in `b`.

    U counts the pairs (x in a, y in b) with x < y (ties count one half). Under
    the null hypothesis every assignment of the pooled ranks to the two groups is
    equally likely; the p-value is the probability of a U at least as large as
    the observed one. Exact by counting, which is cheap for the 5 to 20
    repetitions a benchmark run has. Ties are rare for timings; with ties the
    test is slightly conservative.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 1.0
    u = sum(1.0 if x < y else 0.5 if x == y else 0.0 for x in a for y in b)
    # table[(i, j)][s]: number of orderings of i values of `a` and j values of
    # `b` whose U statistic is s.
    max_u = n * m
    # Place pooled items in increasing order; each is an `a` or a `b`. A `b`
    # placed after i `a`s adds i to U (it beats every `a` before it).
    table = {(0, 0): [1] + [0] * max_u}
    for i in range(n + 1):
        for j in range(m + 1):
            if (i, j) == (0, 0):
                continue
            row = [0] * (max_u + 1)
            if i > 0:
                prev = table[(i - 1, j)]
                for s in range(max_u + 1):
                    row[s] += prev[s]
            if j > 0:
                prev = table[(i, j - 1)]
                for s in range(max_u + 1 - i):
                    row[s + i] += prev[s]
            table[(i, j)] = row
    dist = table[(n, m)]
    total = comb(n + m, n)
    threshold = u - 1e-9
    tail = sum(c for s, c in enumerate(dist) if s >= threshold)
    return tail / total
# [/snippet:mannwhitney]


@dataclass
class Verdict:
    name: str
    ratio: float  # current / baseline, as "speed": > 1 is faster
    p_value: float
    regressed: bool
    note: str = ""


# [snippet:compare]
def compare(baseline: dict[str, Samples], current: dict[str, Samples], threshold: float = 0.05,
            alpha: float = 0.01) -> list[Verdict]:
    """A benchmark regressed if its median speed dropped by more than `threshold`
    and a one-sided Mann-Whitney test says the drop is unlikely to be noise."""
    verdicts = []
    for name, base in sorted(baseline.items()):
        cur = current.get(name)
        if cur is None:
            verdicts.append(Verdict(name, float("nan"), 1.0, False, "missing in current run"))
            continue
        if cur.higher_is_better != base.higher_is_better:
            verdicts.append(Verdict(name, float("nan"), 1.0, True, "metric changed"))
            continue
        # Convert everything to "speed" so that larger is always better.
        def speed(v: list[float]) -> list[float]:
            return v if base.higher_is_better else [1.0 / x for x in v]
        b, c = speed(base.values), speed(cur.values)
        ratio = statistics.median(c) / statistics.median(b)
        p = mann_whitney_p_less(c, b)
        if len(b) < 5 or len(c) < 5:
            verdicts.append(Verdict(name, ratio, p, False, "fewer than 5 repetitions: not judged"))
            continue
        regressed = ratio < 1.0 - threshold and p < alpha
        verdicts.append(Verdict(name, ratio, p, regressed))
    return verdicts
# [/snippet:compare]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline")
    ap.add_argument("current")
    ap.add_argument("--threshold", type=float, default=0.05, help="allowed slowdown (default 0.05)")
    ap.add_argument("--alpha", type=float, default=0.01, help="significance level (default 0.01)")
    ap.add_argument("--strict", action="store_true", help="fail if a baseline benchmark is missing")
    args = ap.parse_args(argv)
    verdicts = compare(load(args.baseline), load(args.current), args.threshold, args.alpha)
    failed = False
    print(f"{'benchmark':60} {'speed':>8} {'p':>8}  verdict")
    for v in verdicts:
        bad = v.regressed or (args.strict and v.note.startswith("missing"))
        failed |= bad
        state = "REGRESSION" if v.regressed else ("FAIL" if bad else "ok")
        print(f"{v.name[:60]:60} {v.ratio:8.3f} {v.p_value:8.4f}  {state} {v.note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
