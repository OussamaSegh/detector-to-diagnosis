# SPDX-License-Identifier: MIT
"""Exercise 27.1: each crystal's efficiency from a normalization scan, and a scan normalized.

counts[i, j] is the coincidences recorded between crystals i and j (symmetric, crystal = ring *
crystals per ring + position); expected[i, j] is what a perfect scanner would record from the same
source (the source's projection times the geometry), known up to a scale. A real scanner records
eff[i] * eff[j] * expected[i, j] on average.
"""
import numpy as np


# [snippet:efficiencies]
def efficiencies(counts, expected, tol=1e-10, max_iter=200):
    """The efficiencies (mean 1) that best explain counts: the fixed point of
    eff[i] = F[i] / sum_j eff[j] expected[i, j], with F[i] the fan sum of crystal i. One step from
    eff = 1 is the fan-sum ratio, exact only when every crystal sees the source alike; the
    iteration removes the source's own pattern and the partners' efficiencies."""
    counts = np.asarray(counts, dtype=float)
    expected = np.asarray(expected, dtype=float)
    fan = counts.sum(axis=1)
    eff = np.ones(fan.size)
    for _ in range(max_iter):
        seen = expected @ eff
        new = np.where(seen > 0, fan / np.where(seen > 0, seen, 1.0), 0.0)
        new /= new.mean()
        # The fixed point alternates around the answer; the geometric mean of two steps damps it.
        new = np.sqrt(new * eff)
        new /= new.mean()
        done = np.abs(new - eff).max() < tol
        eff = new
        if done:
            break
    return eff
# [/snippet:efficiencies]


# [snippet:normalize]
def normalize(counts, eff):
    """counts divided by eff[i] * eff[j], and the crystals with no efficiency: their lines are set
    to 0 (they measured nothing) and named, for the reconstruction to leave out."""
    eff = np.asarray(eff, dtype=float)
    dead = np.flatnonzero(eff <= 0)
    product = np.outer(eff, eff)
    out = np.where(product > 0, counts / np.where(product > 0, product, 1.0), 0.0)
    return out, dead
# [/snippet:normalize]
