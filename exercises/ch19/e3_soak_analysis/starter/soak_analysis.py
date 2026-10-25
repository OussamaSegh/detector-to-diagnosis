# SPDX-License-Identifier: MIT
"""Exercise 19.3 starter: reading a soak test's samples.

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
    # TODO: the slope b of the least-squares line, and its standard error
    # sqrt(sum of squared residuals / (n - 2) / sum((x - mean x)^2)).
    return 0.0, math.inf


def analyze(rows, warmup_s=600.0, max_growth_mib_h=1.0, max_latency_growth_ms_h=1.0,
            min_rate_fraction=0.9):
    problems = []
    # TODO: short, memory, latency (after the warm-up, two standard errors), counter, stall, fault.
    if rows and rows[-1]["losses"] > 0:
        problems.append(("loss", f"{rows[-1]['losses']} singles lost"))
    return problems
