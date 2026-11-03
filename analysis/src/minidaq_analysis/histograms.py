# SPDX-License-Identifier: MIT
"""Histograms of a run, filled in one pass over its chunks.

Everything a quality control report needs is a histogram: the energy spectrum, the time
differences, the counts per crystal and per crystal pair, the counts per time bin. Histograms add
up, so a run of any size is one pass of chunks of a fixed size, and the memory is that of the
histograms, not of the run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from .fitting import Histogram
from .listmode import Coincidences


# [snippet:signed_dt]
def signed_dt_ps(c: Coincidences, delayed_window_ps: int = 0) -> npt.NDArray[np.int64]:
    """Time of the single in the lower-numbered crystal minus time of the one in the higher.

    dt_ps in the file is later minus earlier and never negative: a histogram of it folds the
    timing peak in half. Ordering the pair by crystal instead of by time gives a quantity whose
    distribution is the whole peak, centered on the time of flight. A delayed coincidence's dt_ps
    includes the delay, which is removed first."""
    dt = c.dt_ps.astype(np.int64) - np.where(c.delayed, np.int64(delayed_window_ps), 0)
    return np.where(c.crystal_a < c.crystal_b, -dt, dt)
# [/snippet:signed_dt]


def pair_keys(c: Coincidences, crystals: int) -> npt.NDArray[np.int64]:
    """One integer per unordered crystal pair: lower id times `crystals` plus higher id."""
    lo = np.minimum(c.crystal_a, c.crystal_b).astype(np.int64)
    hi = np.maximum(c.crystal_a, c.crystal_b).astype(np.int64)
    return lo * crystals + hi


# [snippet:pair_counts]
def pair_counts(c: Coincidences, crystals: int) -> tuple[npt.NDArray[np.int64],
                                                         npt.NDArray[np.int64]]:
    """(pair keys, counts) of the pairs present, sorted by key. A dense matrix would have
    crystals^2 / 2 cells (170 million for 18,432 crystals); a run touches a small part of them."""
    keys, counts = np.unique(pair_keys(c, crystals), return_counts=True)
    return keys, counts.astype(np.int64)


def merge_pair_counts(a: tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]],
                      b: tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]
                      ) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    keys = np.concatenate([a[0], b[0]])
    counts = np.concatenate([a[1], b[1]])
    merged, inverse = np.unique(keys, return_inverse=True)
    return merged, np.bincount(inverse, weights=counts, minlength=merged.size).astype(np.int64)
# [/snippet:pair_counts]


@dataclass
class RunHistograms:
    """The histograms of one run. Fill with add(), chunk after chunk, in time order."""

    crystals: int
    delayed_window_ps: int
    energy_edges: npt.NDArray[np.float64] = field(
        default_factory=lambda: np.arange(0.0, 1024.0 + 1.0, 1.0))
    dt_edges: npt.NDArray[np.float64] = field(
        default_factory=lambda: np.arange(-2000.0, 2000.0 + 20.0, 20.0))
    rate_bin_ps: int = 10_000_000_000  # 10 ms

    def __post_init__(self) -> None:
        self.energy = np.zeros(self.energy_edges.size - 1)
        self.dt_prompt = np.zeros(self.dt_edges.size - 1)
        self.dt_delayed = np.zeros(self.dt_edges.size - 1)
        self.per_crystal = np.zeros(self.crystals, dtype=np.int64)
        self.pairs: tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]] = (
            np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64))
        self.rate_prompt = np.zeros(0, dtype=np.int64)
        self.rate_delayed = np.zeros(0, dtype=np.int64)
        self.t0_ps: int | None = None
        self.last_ps: int | None = None
        self.prompts = 0
        self.delayeds = 0
        self.tags = 0
        self.out_of_order = 0

    def add(self, c: Coincidences, tags: int = 0) -> None:
        self.tags += tags
        if len(c) == 0:
            return
        if np.any(c.crystal_a >= self.crystals) or np.any(c.crystal_b >= self.crystals):
            raise ValueError("a crystal id beyond the scanner's crystals")
        if self.t0_ps is None:
            self.t0_ps = int(c.time_ps[0])
        # Time order within the chunk and across chunks (a reset would show here).
        self.out_of_order += int(np.count_nonzero(np.diff(c.time_ps) < 0))
        if self.last_ps is not None and int(c.time_ps[0]) < self.last_ps:
            self.out_of_order += 1
        self.last_ps = int(c.time_ps[-1])

        p = c.select(~c.delayed)
        d = c.select(c.delayed)
        self.prompts += len(p)
        self.delayeds += len(d)
        both = np.concatenate([p.energy_a_kev, p.energy_b_kev])
        self.energy += np.histogram(both, bins=self.energy_edges)[0]
        self.dt_prompt += np.histogram(signed_dt_ps(p), bins=self.dt_edges)[0]
        self.dt_delayed += np.histogram(signed_dt_ps(d, self.delayed_window_ps),
                                        bins=self.dt_edges)[0]
        self.per_crystal += np.bincount(p.crystal_a, minlength=self.crystals)
        self.per_crystal += np.bincount(p.crystal_b, minlength=self.crystals)
        self.pairs = merge_pair_counts(self.pairs, pair_counts(p, self.crystals))
        self.rate_prompt = _add_rate(self.rate_prompt, p.time_ps, self.t0_ps, self.rate_bin_ps)
        self.rate_delayed = _add_rate(self.rate_delayed, d.time_ps, self.t0_ps, self.rate_bin_ps)

    def energy_histogram(self) -> Histogram:
        return Histogram(self.energy.copy(), self.energy_edges)

    def dt_histogram(self, delayed: bool = False) -> Histogram:
        return Histogram((self.dt_delayed if delayed else self.dt_prompt).copy(), self.dt_edges)


def _add_rate(acc: npt.NDArray[np.int64], t_ps: npt.NDArray[np.int64], t0: int,
              bin_ps: int) -> npt.NDArray[np.int64]:
    if t_ps.size == 0:
        return acc
    idx = (t_ps - t0) // bin_ps
    if np.any(idx < 0):
        raise ValueError("a time before the run's first coincidence")
    counts = np.bincount(idx, minlength=acc.size)
    if counts.size > acc.size:
        acc = np.concatenate([acc, np.zeros(counts.size - acc.size, dtype=np.int64)])
    acc[: counts.size] += counts
    return acc
