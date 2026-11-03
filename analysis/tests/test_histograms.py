# SPDX-License-Identifier: MIT
"""The time difference ordered by crystal, and histograms that add up chunk by chunk."""
from __future__ import annotations

import pathlib

import mdql
import numpy as np
from conftest import CRYSTALS, DELAY_PS, synthetic

from minidaq_analysis import fitting as F
from minidaq_analysis.histograms import RunHistograms, pair_counts, signed_dt_ps
from minidaq_analysis.listmode import ListModeFile


def coincidences(tmp_path: pathlib.Path, r: dict[str, np.ndarray]):  # type: ignore[no-untyped-def]
    p = tmp_path / "f.mdql"
    p.write_bytes(mdql.file_bytes(r, block_records=1000))
    with ListModeFile(p) as f:
        return f.coincidences()


def test_the_signed_difference_is_the_whole_peak(tmp_path: pathlib.Path,
                                                 rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-003
    c = coincidences(tmp_path, synthetic(rng, 40_000, tof_ps=-120.0, delayed_fraction=0.0))
    assert np.all(c.dt_ps >= 0)  # as stored: later minus earlier
    s = signed_dt_ps(c)
    edges = np.arange(-1500.0, 1520.0, 20.0)
    r = F.fit_timing(F.Histogram.of(s, edges))
    ctr, ctr_err = F.fwhm(r)
    assert abs(ctr - 300.0) < 4 * ctr_err
    assert abs(r["mean"][0] + 120.0) < 4 * r["mean"][1]
    # The folded quantity is not the peak: its "FWHM" is about half and it has no center.
    folded = F.fit_timing(F.Histogram.of(c.dt_ps, edges))
    assert F.fwhm(folded)[0] < 0.8 * ctr or abs(folded["mean"][0]) > 50


def test_delayeds_lose_their_delay(tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-003
    c = coincidences(tmp_path, synthetic(rng, 20_000, delayed_fraction=0.5))
    s = signed_dt_ps(c.select(c.delayed), DELAY_PS)
    assert s.min() >= -2000 and s.max() <= 2000 and abs(s.mean()) < 50


def test_pair_counts_merge_to_the_counts_of_the_whole(tmp_path: pathlib.Path,
                                                      rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-003
    c = coincidences(tmp_path, synthetic(rng, 30_000, delayed_fraction=0.0))
    keys, counts = pair_counts(c, CRYSTALS)
    assert counts.sum() == len(c)
    lo = np.minimum(c.crystal_a, c.crystal_b)
    hi = np.maximum(c.crystal_a, c.crystal_b)
    k = 1234
    assert counts[np.searchsorted(keys, lo[k] * CRYSTALS + hi[k])] == np.count_nonzero(
        (lo == lo[k]) & (hi == hi[k]))


def test_the_histograms_do_not_depend_on_the_chunks(tmp_path: pathlib.Path,
                                                    rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-003
    p = tmp_path / "f.mdql"
    p.write_bytes(mdql.file_bytes(synthetic(rng, 20_000), block_records=700))
    results = []
    for chunk in (700, 5000, 1 << 20):
        h = RunHistograms(CRYSTALS, DELAY_PS)
        with ListModeFile(p) as f:
            for c, tags in f.chunks(chunk):
                h.add(c, tags)
        results.append(h)
    a = results[0]
    for b in results[1:]:
        np.testing.assert_array_equal(a.energy, b.energy)
        np.testing.assert_array_equal(a.dt_prompt, b.dt_prompt)
        np.testing.assert_array_equal(a.dt_delayed, b.dt_delayed)
        np.testing.assert_array_equal(a.per_crystal, b.per_crystal)
        np.testing.assert_array_equal(a.pairs[0], b.pairs[0])
        np.testing.assert_array_equal(a.pairs[1], b.pairs[1])
        np.testing.assert_array_equal(a.rate_prompt, b.rate_prompt)
        assert (a.prompts, a.delayeds, a.out_of_order) == (b.prompts, b.delayeds, 0)
