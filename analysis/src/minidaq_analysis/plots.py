# SPDX-License-Identifier: MIT
"""Figures for reports, drawn the same way every time.

The conventions (Chapter 31, "Plots that are evidence"): every axis has a quantity and a unit;
data are drawn with their Poisson uncertainty, the model as a line over the fitted range only; a
fit has a panel of normalized residuals, (n - mu) / sqrt(mu), with lines at -2 and +2, so a reader
sees at a glance whether the model describes the data; the numbers in the legend carry their
uncertainties; the figure is written at 300 dpi with a non-interactive backend, so a script on a
headless machine gives the same picture as a notebook.
"""
from __future__ import annotations

import pathlib
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import fitting
from .histograms import RunHistograms

DPI = 300
# Typed as Any: matplotlib's stubs want a dict of literal key names.
STYLE: Any = {"figure.figsize": (6.4, 4.8), "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
              "savefig.bbox": "tight"}


# [snippet:fit_figure]
def fit_figure(r: fitting.FitResult, xlabel: str, unit: str, label: str,
               path: pathlib.Path) -> None:
    """The fitted bins with their uncertainties, the model, and the normalized residuals."""
    hist = r.hist
    with plt.rc_context(STYLE):
        fig, (ax, res) = plt.subplots(2, 1, sharex=True, height_ratios=(3, 1))
        c, n = hist.centers, hist.counts
        ax.errorbar(c, n, yerr=np.sqrt(np.maximum(n, 1.0)), fmt=".", ms=2, lw=0.6,
                    color="0.2", label="data")
        ax.plot(c, r.expected, color="C3", lw=1.2, label=label)
        ax.set_ylabel(f"counts per {np.mean(np.diff(hist.edges)):g} {unit}")
        ax.legend(loc="upper left", frameon=False)
        pull = (n - r.expected) / np.sqrt(np.maximum(r.expected, 1e-9))
        res.plot(c, pull, ".", ms=2, color="0.2")
        for y in (-2.0, 0.0, 2.0):
            res.axhline(y, color="C3" if y == 0 else "0.5", lw=0.6, ls="-" if y == 0 else "--")
        res.set_ylabel("(n - μ)/√μ")
        res.set_xlabel(f"{xlabel} ({unit})")
        fig.savefig(path, dpi=DPI)
        plt.close(fig)
# [/snippet:fit_figure]


def energy(h: RunHistograms, r: fitting.FitResult, path: pathlib.Path) -> None:
    mean, mean_err = r["mean"]
    res, res_err = fitting.fwhm_fraction(r)
    fit_figure(r, "energy", "keV",
               f"Gaussian + line: {mean:.1f} ± {mean_err:.1f} keV, "
               f"FWHM {100 * res:.2f} ± {100 * res_err:.2f}%", path)


def timing(h: RunHistograms, r: fitting.FitResult, path: pathlib.Path) -> None:
    ctr, ctr_err = fitting.fwhm(r)
    mean, mean_err = r["mean"]
    fit_figure(r, "time difference, lower minus higher crystal", "ps",
               f"Gaussian + constant: FWHM {ctr:.0f} ± {ctr_err:.0f} ps, "
               f"center {mean:.1f} ± {mean_err:.1f} ps", path)


def rate(h: RunHistograms, path: pathlib.Path) -> None:
    """Prompts and delayeds per time bin; the band is the mean prompt count ± 3 √mean."""
    bin_s = h.rate_bin_ps * 1e-12
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots()
        full = h.rate_prompt[:-1]
        t = np.arange(full.size) * bin_s
        ax.step(t, full / bin_s, where="post", lw=0.8, color="0.2", label="prompts")
        d = h.rate_delayed[: full.size]
        ax.step(t[: d.size], d / bin_s, where="post", lw=0.8, color="C0", label="delayeds")
        m = full.mean()
        ax.axhspan((m - 3 * np.sqrt(m)) / bin_s, (m + 3 * np.sqrt(m)) / bin_s, color="C3",
                   alpha=0.15, label="prompt mean ± 3√mean")
        ax.set_xlabel("time since the first coincidence (s)")
        ax.set_ylabel(f"rate (1/s), {1e3 * bin_s:g} ms bins")
        ax.set_ylim(bottom=0)
        ax.legend(loc="center right", frameon=False)
        fig.savefig(path, dpi=DPI)
        plt.close(fig)
