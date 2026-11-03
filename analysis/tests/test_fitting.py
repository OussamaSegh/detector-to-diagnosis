# SPDX-License-Identifier: MIT
# REQ: SRS-ANA-002
"""Fits: right values, right uncertainties, and loud failures."""
from __future__ import annotations

import math

import numpy as np
import pytest

from minidaq_analysis import fitting as F

EDGES = np.arange(400.0, 621.0, 1.0)
TRUE = np.array([20_000.0, 511.0, 26.0, 35.0, 24.0])  # area, mean, sigma, b_low, b_high
MODEL = F.gaussian_plus_line(400.0, 620.0)


def poisson_histogram(rng: np.random.Generator, p: np.ndarray, edges: np.ndarray = EDGES,
                      model: F.Model = MODEL) -> F.Histogram:
    mu = model(edges[:-1], edges[1:], p)
    return F.Histogram(rng.poisson(mu).astype(np.float64), edges)


def test_bin_integrated_gaussian_holds_its_area() -> None:
    edges = np.arange(-50.0, 50.5, 0.5)
    counts = F.gaussian_counts(edges[:-1], edges[1:], 1000.0, 1.3, 4.0)
    assert counts.sum() == pytest.approx(1000.0, rel=1e-9)
    # Bins as wide as the peak: exact integration still holds, where centre * width would not.
    wide = np.arange(-40.0, 41.0, 8.0)
    assert F.gaussian_counts(wide[:-1], wide[1:], 1000.0, 1.3, 4.0).sum() == pytest.approx(1000.0)


def test_recovers_the_true_parameters(rng: np.random.Generator) -> None:
    r = F.fit_photopeak(poisson_histogram(rng, TRUE), 440.0, 580.0)
    for name, true in zip(("area", "mean", "sigma"), TRUE[:3], strict=True):
        value, error = r[name]
        assert abs(value - true) < 4 * error, name
    assert 0.5 < r.statistic / r.ndf < 1.5
    res, res_err = F.fwhm_fraction(r)
    assert abs(res - F.SIGMA_TO_FWHM * 26.0 / 511.0) < 4 * res_err


# [snippet:pulls]
@pytest.mark.slow
def test_the_errors_are_the_spread_of_the_estimates(rng: np.random.Generator) -> None:
    """Over repeated histograms, (estimate - truth) / error must have mean 0 and SD 1: a fit
    whose errors were too small (or too large) by 15% fails."""
    pulls = []
    for _ in range(300):
        r = F.fit_photopeak(poisson_histogram(rng, TRUE), 440.0, 580.0)
        pulls.append([(r[n][0] - t) / r[n][1] for n, t in zip(("area", "mean", "sigma"),
                                                               TRUE[:3], strict=True)])
    p = np.array(pulls)
    assert np.all(np.abs(p.mean(axis=0)) < 0.15), p.mean(axis=0)
    assert np.all(np.abs(p.std(axis=0, ddof=1) - 1.0) < 0.15), p.std(axis=0, ddof=1)
# [/snippet:pulls]


def test_neyman_least_squares_underestimates_a_weak_peak(rng: np.random.Generator) -> None:
    """At a few counts per bin, weighting by the observed counts pulls the area down; maximum
    likelihood does not (the bias the chapter measures)."""
    weak = np.array([400.0, 511.0, 26.0, 0.5, 0.5])
    ney, poi = [], []
    for _ in range(200):
        h = poisson_histogram(rng, weak)
        ney.append(F.fit_photopeak(h, 440.0, 580.0, "neyman")["area"][0])
        poi.append(F.fit_photopeak(h, 440.0, 580.0, "poisson")["area"][0])
    sem = np.std(poi, ddof=1) / math.sqrt(len(poi))
    assert abs(np.mean(poi) - 400.0) < 4 * sem
    assert np.mean(ney) < 400.0 - 20.0  # more than 5% low


def test_derived_errors_include_the_correlation() -> None:
    """FWHM/E from a covariance with a correlation: the propagated error equals the analytic
    one, and differs from the error that ignores the correlation."""
    values = np.array([1.0, 500.0, 20.0])
    cov = np.array([[0, 0, 0], [0, 4.0, 1.5], [0, 1.5, 1.0]])
    r = F.FitResult(("area", "mean", "sigma"), values, cov, 0.0, 1, "poisson",
                    np.zeros(1), F.Histogram(np.zeros(1), np.array([0.0, 1.0])))
    value, err = F.fwhm_fraction(r)
    k = F.SIGMA_TO_FWHM
    g = np.array([0.0, -k * 20.0 / 500.0**2, k / 500.0])
    assert value == pytest.approx(k * 20.0 / 500.0)
    assert err == pytest.approx(math.sqrt(g @ cov @ g), rel=1e-6)
    assert err != pytest.approx(math.sqrt(g[1] ** 2 * 4.0 + g[2] ** 2 * 1.0), rel=1e-3)


def test_a_fit_that_cannot_work_raises_instead_of_returning_a_number() -> None:
    empty = F.Histogram(np.zeros(EDGES.size - 1), EDGES)
    with pytest.raises(ValueError, match="too few"):
        F.fit_photopeak(empty, 440.0, 580.0)
    flat = F.Histogram(np.full(EDGES.size - 1, 100.0), EDGES)
    with pytest.raises(RuntimeError):
        # A Gaussian on a flat line with no peak: the area and the width are not determined.
        F.fit(flat.window(440, 580), F.gaussian_plus_constant, [0.0, 511.0, 26.0, 100.0],
              ("area", "mean", "sigma", "background"), "poisson",
              [(0.0, None), (440.0, 580.0), (1.0, 140.0), (0.0, None)])


def test_refuses_more_parameters_than_bins() -> None:
    h = F.Histogram(np.array([1.0, 2.0, 3.0]), np.array([0.0, 1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="3 bins for 4 parameters"):
        F.fit(h, F.gaussian_plus_constant, [1, 1, 1, 1], ("a", "b", "c", "d"))
