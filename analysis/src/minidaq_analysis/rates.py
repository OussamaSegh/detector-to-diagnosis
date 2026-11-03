# SPDX-License-Identifier: MIT
"""Is the count rate of a run steady? A test of constancy and a search for dips.

A run of a long-lived source at a steady activity should give Poisson counts per time bin around
one mean. Lost blocks, a stalled receiver or a detector that drops out show as bins far below it.
Two questions, two tests:

- constancy: the dispersion statistic sum((n_i - mean)^2 / mean), which is chi-square with
  bins - 1 degrees of freedom for Poisson counts of a constant rate;
- dips: the probability of the lowest bin's count or fewer, times the number of bins (a Bonferroni
  bound on the chance of seeing such a dip anywhere in the run).

A decaying source is not constant: over a run of T seconds of a source with half-life T_half the
rate falls by a factor 2^(-T / T_half); the report states the run length so a reader can judge
(18F: 0.6% over a minute).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats


@dataclass(frozen=True)
class RateCheck:
    bins: int
    mean_per_bin: float
    dispersion: float  # sum((n - mean)^2 / mean)
    p_constant: float
    lowest: int
    p_dip: float  # min(1, bins * P(N <= lowest)), N Poisson with the mean


# [snippet:rate_check]
def check_rate(counts: npt.NDArray[np.int64]) -> RateCheck:
    """Tests counts of full time bins (leave out a partial last bin) for a constant rate."""
    n = np.asarray(counts, dtype=np.float64)
    if n.size < 2:
        raise ValueError("at least two full time bins are needed")
    mean = float(n.mean())
    if mean <= 0:
        raise ValueError("no counts")
    dispersion = float(np.sum((n - mean) ** 2) / mean)
    p_constant = float(stats.chi2.sf(dispersion, n.size - 1))
    lowest = int(np.min(n))
    p_dip = float(min(1.0, n.size * stats.poisson.cdf(lowest, mean)))
    return RateCheck(int(n.size), mean, dispersion, p_constant, lowest, p_dip)
# [/snippet:rate_check]
