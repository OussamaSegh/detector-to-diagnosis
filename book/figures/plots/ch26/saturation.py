# SPDX-License-Identifier: MIT
"""Figure for Chapter 26: the SiPM's saturation, S(E) = E_sat (1 - exp(-E / E_sat)) with E_sat
1500 keV, and how far a quadratic fitted to its inverse over 200 to 700 keV, or over 100 to 700
keV, is from the exact inverse.

    python3 book/tools/figures.py build book/figures/plots/ch26/saturation.py screen 6 pdf
"""
import sys

import numpy as np

import d2d

ESAT = 1500.0


def main(dst):
    fig, (ax, bx) = d2d.figure(height=2.0, width=1.0, ncols=2)
    e = np.linspace(0, 800, 400)
    s = ESAT * (1 - np.exp(-e / ESAT))
    ax.plot(e, e, color=d2d.MUTED, lw=d2d.LINE_PT, ls="--")
    ax.plot(e, s, color=d2d.PART, lw=d2d.LINE_PT * 1.4)
    ax.plot([511, 511], [0, 433], color=d2d.CAT[0], lw=0.7, ls=":")
    ax.plot([0, 511], [433, 433], color=d2d.CAT[0], lw=0.7, ls=":")
    ax.scatter([511], [433], color=d2d.CAT[0], s=16, zorder=3)
    ax.text(540, 330, "511 keV reads as 433,\n15% low", fontsize=d2d.FONT_PT - 1, color=d2d.CAT[0], va="top")
    d2d.label(ax, 560, 640, "linear", d2d.MUTED)
    d2d.label(ax, 640, 455, "saturating SiPM", d2d.PART)
    ax.set_xlabel("energy deposited, keV")
    ax.set_ylabel("response, keV equivalent")
    ax.set_xlim(0, 800)
    ax.set_ylim(0, 800)
    for k, (lo, lab) in enumerate([(200, "fitted on 200 to 700 keV"), (100, "fitted on 100 to 700 keV")]):
        ss = np.linspace(ESAT * (1 - np.exp(-lo / ESAT)), ESAT * (1 - np.exp(-700 / ESAT)), 200)
        exact = -ESAT * np.log(1 - ss / ESAT)
        q = np.polyfit(ss, exact, 2)
        err = (np.polyval(q, ss) - exact) / exact * 100
        bx.plot(exact, err, color=d2d.PART if k == 0 else d2d.CAT[0], ls=d2d.DASHES[k], lw=d2d.LINE_PT * 1.2, label=lab)
    bx.axvspan(435, 585, color=d2d.tint(d2d.PART, 0.15), lw=0)
    bx.axhline(0, color=d2d.MUTED, lw=0.6)
    bx.set_xlabel("energy, keV")
    bx.set_ylabel("quadratic minus exact, %")
    bx.set_xlim(80, 720)
    bx.legend(loc="upper center", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
