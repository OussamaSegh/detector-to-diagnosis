# SPDX-License-Identifier: MIT
"""Exercise 30.3: acceptance limits and trends for a recurring image quality check.

A site measures the same figure of merit (a rod's contrast recovery, say) on the same phantom
every week. A baseline of results, taken when the scanner was accepted, sets the limits; each new
result is reviewed against them.
"""
import numpy as np


def limits(baseline, k=3.0):
    """(low, high): the mean of the results, plus and minus k standard deviations."""
    b = np.asarray(baseline, dtype=np.float64)
    return float(b.mean() - k * b.std()), float(b.mean() + k * b.std())


def review(results, baseline, k=3.0, run=7):
    """The findings for results, in time order: a list of (index, kind). The limits come from all
    the results there are."""
    everything = np.concatenate([np.asarray(baseline, dtype=np.float64),
                                 np.asarray(results, dtype=np.float64)])
    low, high = limits(everything, k)
    return [(i, "out") for i, v in enumerate(results) if v < low or v > high]
