# SPDX-License-Identifier: MIT
"""Figure for Chapter 26: energy spectra of an uncalibrated detector and after calibration, from the
simulator's model (gain spread 10%, E_sat 1500 keV, 12% FWHM at 511 keV), drawn with a fixed seed.
Left, four crystals as the board reports them against MiniDAQ's energy window; right, the summed
spectrum of 2,000 crystals before and after calibration.

    python3 book/tools/figures.py build book/figures/plots/ch26/spectra.py screen 6 pdf
"""
import sys

import numpy as np

import d2d

ESAT = 1500.0


def deposits(rng, n):
    """Energies deposited by 511 keV photons: a photopeak and a Compton continuum below 340 keV."""
    peak = rng.random(n) < 0.45
    e = np.where(peak, 511.0, rng.uniform(30, 340, n) ** 1.0)
    return e * (1 + rng.normal(0, 0.12 / 2.355, n) * np.sqrt(511.0 / np.maximum(e, 30)))


def response(e, gain):
    return gain * ESAT * (1 - np.exp(-e / ESAT))


def main(dst):
    rng = np.random.default_rng(26)
    fig, (ax, bx) = d2d.figure(height=2.1, width=1.0, ncols=2, sharey=False)
    bins = np.arange(0, 800, 5)
    for ax_ in (ax, bx):
        ax_.axvspan(435, 585, color=d2d.tint(d2d.PART, 0.15), lw=0)
    for k, g in enumerate([0.85, 0.95, 1.08, 1.2]):
        h, _ = np.histogram(response(deposits(rng, 60000), g), bins)
        ax.step(bins[:-1], h / h.max(), where="post", color=d2d.CAT[k], lw=d2d.LINE_PT, ls=d2d.DASHES[k],
                label=f"gain {g:.2f}")
    ax.set_title("four crystals, as reported", fontsize=d2d.FONT_PT, color=d2d.INK)
    ax.text(510, 1.45, "energy window", ha="center", fontsize=d2d.FONT_PT - 1, color=d2d.PART)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    gains = np.clip(rng.normal(1.0, 0.1, 2000), 0.6, 1.6)
    e = deposits(rng, 2000 * 150)
    raw = response(e, np.repeat(gains, 150))
    cal = e
    for k, (vals, lab, c) in enumerate([(raw, "uncalibrated: peak 435 keV, 23% FWHM", d2d.MUTED),
                                        (cal, "calibrated: peak 511 keV, 12% FWHM", d2d.PART)]):
        h, _ = np.histogram(vals, bins)
        bx.step(bins[:-1], h / h.max(), where="post", color=c, lw=d2d.LINE_PT * (1.4 if k else 1), label=lab)
    bx.set_title("2,000 crystals summed", fontsize=d2d.FONT_PT, color=d2d.INK)
    bx.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.2, frameon=False, bbox_to_anchor=(0, 0.93))
    for ax_ in (ax, bx):
        ax_.set_xlim(0, 800)
        ax_.set_ylim(0, 1.55)
        ax_.set_xlabel("energy, keV")
        ax_.set_yticks([])
    ax.set_ylabel("counts, scaled")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
