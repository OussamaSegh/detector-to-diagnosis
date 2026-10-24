#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise 5.3 starter: performance regression gate for Google Benchmark results.

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
    # TODO: compute U, then its exact null distribution by counting the
    # orderings of len(a) + len(b) pooled values (dynamic programming), and
    # return P(U >= observed).
    raise NotImplementedError("mann_whitney_p_less")


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
    # TODO: for every baseline benchmark, compare medians as speeds (larger is
    # better), test significance, and handle missing benchmarks and runs with
    # fewer than 5 repetitions (see the README and the tests).
    raise NotImplementedError("compare")


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
