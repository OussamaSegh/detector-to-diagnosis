# SPDX-License-Identifier: MIT
"""Exercise 27.1: each crystal's efficiency from a normalization scan, and a scan normalized.

counts[i, j] is the coincidences recorded between crystals i and j (symmetric, crystal = ring *
crystals per ring + position); expected[i, j] is what a perfect scanner would record from the same
source (the source's projection times the geometry), known up to a scale. A real scanner records
eff[i] * eff[j] * expected[i, j] on average.

This starter runs and its efficiencies look plausible for a centered source. TODO: make the tests
pass.
"""
import numpy as np


def efficiencies(counts, expected, tol=1e-10, max_iter=200):
    """The efficiencies (mean 1) that best explain counts."""
    # Every crystal of a centered source sees the same activity: its fan sum over the mean fan
    # sum is its efficiency.
    fan = np.asarray(counts, dtype=float).sum(axis=1)
    return fan / fan.mean()


def normalize(counts, eff):
    """counts corrected for the efficiencies of the two crystals of each line, and the crystals
    with no efficiency."""
    eff = np.asarray(eff, dtype=float)
    pair = 0.5 * (eff[:, None] + eff[None, :])  # the mean efficiency of the line's two crystals
    return counts / pair, np.array([], dtype=int)
