# SPDX-License-Identifier: MIT
"""Shared helpers: a synthetic run whose truth is known."""
from __future__ import annotations

import pathlib
import sys
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mdql

CRYSTALS = 576 * 32
DELAY_PS = 100_000


def synthetic(rng: np.random.Generator, n: int, seconds: float = 1.0, ctr_ps: float = 300.0,
              resolution: float = 0.12, tof_ps: float = 0.0, delayed_fraction: float = 0.01,
              window_ps: int = 4000) -> dict[str, Any]:
    """n coincidences at a constant rate: crystal pairs at random, a Gaussian timing peak of FWHM
    ctr_ps centered on tof_ps (lower crystal minus higher), Gaussian energies of FWHM/E
    `resolution` around 511 keV, and a fraction of delayeds flat over the window."""
    t = np.sort(rng.integers(0, int(seconds * 1e12), n))
    lo = rng.integers(0, CRYSTALS - 1, n)
    hi = lo + 1 + (rng.integers(0, CRYSTALS - 1, n) % (CRYSTALS - 1 - lo))
    delayed = rng.random(n) < delayed_fraction
    signed = np.where(delayed, rng.uniform(-window_ps / 2, window_ps / 2, n),
                      rng.normal(tof_ps, ctr_ps / 2.3548200450309493, n))
    signed = np.rint(signed).astype(np.int64)
    lo_first = signed <= 0  # t_lo - t_hi <= 0: the lower crystal's single is the earlier
    a = np.where(lo_first, lo, hi)
    b = np.where(lo_first, hi, lo)
    dt = np.abs(signed) + np.where(delayed, DELAY_PS, 0)
    sigma_e = resolution * 511.0 / 2.3548200450309493
    ea, eb = rng.normal(511.0, sigma_e, n), rng.normal(511.0, sigma_e, n)
    return mdql.records(t, a, b, dt, ea, eb, delayed)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(31)
