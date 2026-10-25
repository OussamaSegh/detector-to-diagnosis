# SPDX-License-Identifier: MIT
"""Exercise 19.3 solution: reading a soak test's samples.

A soak test samples a long run every few seconds: the server's resident memory, its counters, its
latency. analyze() turns the samples into a verdict: a list of problems, each a (kind, detail)
pair, empty when the run passed. The kinds are:

  short    fewer than three samples after the warm-up: the trends cannot be judged
  memory   resident memory grows faster than max_growth_mib_h after the warm-up
  latency  the p99 latency grows faster than max_latency_growth_ms_h after the warm-up
  counter  a counter that only counts up went down (it wrapped, or was reset)
  stall    the input rate of one interval fell below min_rate_fraction of the median rate
  loss     the run lost data
  fault    the run reported a fault or left the running state before the last sample

A trend counts only when it is larger than the limit by two standard errors of the slope, so
that noise alone does not fail a run; the warm-up is left out, because memory and latency
settle in the first minutes (pools fill, pages are touched, caches warm).
"""
from __future__ import annotations

import csv
import math
import statistics

COLUMNS = {"t_s": float, "rss_kib": int, "singles_in": int, "losses": int, "state": str,
           "fault": str, "p99_ms": float, "max_ms": float}


def load_csv(path):
    """The rows of a samples.csv written by tools/soak.py, with numbers as numbers."""
    with open(path, newline="") as f:
        return [{k: COLUMNS.get(k, str)(v) for k, v in row.items()} for row in csv.DictReader(f)]


def slope(xs, ys):
    """Least-squares slope of ys over xs, and its standard error."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    residual = sum((y - my - b * (x - mx)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(residual / (n - 2) / sxx) if n > 2 else math.inf
    return b, se


# [snippet:trend]
def _trend(rows, key, scale, limit, kind, unit):
    b, se = slope([r["t_s"] / 3600 for r in rows], [r[key] * scale for r in rows])
    if b - 2 * se > limit:
        return [(kind, f"{key} grows {b:.3f} {unit}/h (standard error {se:.3f}), limit {limit}")]
    return []
# [/snippet:trend]


def analyze(rows, warmup_s=600.0, max_growth_mib_h=1.0, max_latency_growth_ms_h=1.0,
            min_rate_fraction=0.9):
    problems = []
    after = [r for r in rows if r["t_s"] >= warmup_s]
    if len(after) < 3:
        problems.append(("short", f"{len(after)} samples after a warm-up of {warmup_s:g} s"))
    else:
        problems += _trend(after, "rss_kib", 1 / 1024, max_growth_mib_h, "memory", "MiB")
        problems += _trend(after, "p99_ms", 1.0, max_latency_growth_ms_h, "latency", "ms")

    for key in ("singles_in", "losses"):
        for a, b in zip(rows, rows[1:]):
            if b[key] < a[key]:
                problems.append(("counter", f"{key} went from {a[key]} to {b[key]} at {b['t_s']:g} s"))
                break

    rates = [(b["singles_in"] - a["singles_in"]) / (b["t_s"] - a["t_s"]) for a, b in zip(rows, rows[1:])
             if b["t_s"] > a["t_s"]]
    if rates:
        typical = statistics.median(rates)
        for (a, b), rate in zip(zip(rows, rows[1:]), rates):
            if rate < min_rate_fraction * typical:
                problems.append(("stall", f"{rate:.0f}/s from {a['t_s']:g} s to {b['t_s']:g} s, "
                                          f"median {typical:.0f}/s"))
                break

    if rows and rows[-1]["losses"] > 0:
        problems.append(("loss", f"{rows[-1]['losses']} singles lost"))
    for i, r in enumerate(rows):
        if r["fault"] or (r["state"] != "running" and i < len(rows) - 1):
            problems.append(("fault", f"state {r['state']}, fault '{r['fault']}' at {r['t_s']:g} s"))
            break
    return problems
