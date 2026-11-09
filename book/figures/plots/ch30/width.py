# SPDX-License-Identifier: MIT
"""Figure for Chapter 30: measuring a width the way NEMA NU 2 does, with the chapter's own
tools/recon/quality.py. A Gaussian of 3.5 samples FWHM, centred between two samples: the parabola
through the highest sample and its neighbours gives the maximum, and each side's crossing of half
(and a tenth) of it is interpolated linearly between the samples around it.

    python3 book/tools/figures.py build book/figures/plots/ch30/width.py screen 6 pdf tools/recon/quality.py
"""
import pathlib
import sys

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.recon import quality  # noqa: E402

FWHM = 3.5


def main(dst):
    sigma = FWHM / 2.3548
    x = np.arange(-6, 7) + 0.5
    p = np.exp(-0.5 * (x / sigma) ** 2)
    k0, top = quality.parabolic_peak(p)
    fwhm = quality.width(p, 1.0, 0.5)
    fwtm = quality.width(p, 1.0, 0.1)
    fig, ax = d2d.figure(height=2.1, width=0.75)
    xx = np.linspace(-6, 7, 400)
    ax.plot(xx, np.exp(-0.5 * (xx / sigma) ** 2), color=d2d.MUTED, lw=0.8, ls=":", label="the true profile")
    ax.vlines(x, 0, p, color=d2d.tint(d2d.CAT[0], 0.6), lw=2.2)
    ax.scatter(x, p, color=d2d.CAT[0], s=12, zorder=3, label="the samples (pixels)")
    k = int(p.argmax())
    a, b, c = p[k - 1], p[k], p[k + 1]
    t = np.linspace(-1.2, 1.2, 50)
    ax.plot(x[k] + t, b + 0.5 * (c - a) * t + 0.5 * (a - 2 * b + c) * t ** 2, color=d2d.PART, lw=d2d.LINE_PT * 1.3,
            label="parabola through the top three")
    xpk = x[0] + k0
    ax.scatter([xpk], [top], color=d2d.PART, marker="D", s=16, zorder=4)
    for frac, w, c in ((0.5, fwhm, d2d.CAT[2]), (0.1, fwtm, d2d.CAT[3])):
        ax.hlines(frac * top, xpk - w / 2, xpk + w / 2, color=c, lw=1.4)
        ax.text(xpk + w / 2 + 0.25, frac * top, f"{'FWHM' if frac == 0.5 else 'FWTM'} {w:.2f} samples", va="center",
                fontsize=d2d.FONT_PT - 1, color=c)
    ax.text(xpk + 0.3, top + 0.04, f"maximum {top:.3f}\n(highest sample {p.max():.3f})", fontsize=d2d.FONT_PT - 1.2,
            color=d2d.PART, va="bottom")
    ax.set_xlabel("position, samples")
    ax.set_ylabel("value")
    ax.set_ylim(0, 1.3)
    ax.set_xlim(-6, 7)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.3, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
