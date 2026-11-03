# SPDX-License-Identifier: MIT
# REQ: SRS-ANA-004
"""The rate checks: a steady Poisson rate passes as often as it should; a dip is found."""
from __future__ import annotations

import numpy as np
import pytest

from minidaq_analysis.rates import check_rate


def test_a_constant_rate_is_rejected_at_the_stated_rate(rng: np.random.Generator) -> None:
    p = np.array([check_rate(rng.poisson(1000.0, 200)).p_constant for _ in range(2000)])
    # p is uniform for a constant rate: 5% of runs below 0.05, within the binomial spread.
    assert abs(np.mean(p < 0.05) - 0.05) < 3 * np.sqrt(0.05 * 0.95 / p.size)


def test_one_missing_block_is_a_dip(rng: np.random.Generator) -> None:
    counts = rng.poisson(1000.0, 200)
    assert check_rate(counts).p_dip > 0.01
    counts[57] -= 160  # one block of 160 coincidences lost in a bin of 1,000
    r = check_rate(counts)
    assert r.p_dip < 0.001 and r.lowest == counts[57]


def test_needs_two_bins_and_counts() -> None:
    with pytest.raises(ValueError):
        check_rate(np.array([10]))
    with pytest.raises(ValueError):
        check_rate(np.zeros(5, dtype=np.int64))
