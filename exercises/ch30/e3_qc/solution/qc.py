# SPDX-License-Identifier: MIT
"""Exercise 30.3: acceptance limits and trends for a recurring image quality check.

A site measures the same figure of merit (a rod's contrast recovery, say) on the same phantom
every week. A baseline of results, taken when the scanner was accepted, sets the limits; each new
result is reviewed against them.
"""
import numpy as np

MIN_BASELINE = 5


def limits(baseline, k=3.0):
    """(low, high): the baseline's mean plus and minus k sample standard deviations (n - 1).
    ValueError for fewer than MIN_BASELINE results: two or three say little about the spread."""
    b = np.asarray(baseline, dtype=np.float64)
    if b.size < MIN_BASELINE:
        raise ValueError(f"{b.size} baseline results, at least {MIN_BASELINE} are needed")
    m, s = b.mean(), b.std(ddof=1)
    return float(m - k * s), float(m + k * s)


def review(results, baseline, k=3.0, run=7):
    """The findings for results, in time order: (index, "out") for a result outside the
    baseline's limits, and (index, "run") where run results in a row have fallen on the same side
    of the baseline's mean, a shift too small to leave the limits. The limits stay those of the
    baseline: results under review never move them."""
    low, high = limits(baseline, k)
    mean = float(np.mean(baseline))
    findings = []
    side, count = 0, 0
    for i, v in enumerate(np.asarray(results, dtype=np.float64)):
        if v < low or v > high:
            findings.append((i, "out"))
        s = int(np.sign(v - mean))
        count = count + 1 if s != 0 and s == side else (1 if s != 0 else 0)
        side = s
        if count == run:
            findings.append((i, "run"))
    return findings
