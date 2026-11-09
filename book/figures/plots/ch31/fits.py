# SPDX-License-Identifier: MIT
"""Figure for Chapter 31: the bias of a peak's fitted area against the counts in the peak, least
squares weighted by the counts (Neyman) against Poisson maximum likelihood, 400 histograms per point,
from section 2 of measurements/ch31/analysis.txt.

    python3 book/tools/figures.py build book/figures/plots/ch31/fits.py screen 7 pdf measurements/ch31/analysis.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch31/analysis.txt"


def main(dst):
    text = SRC.read_text().split("## 2.")[1].split("## 3.")[0]
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")][1:]
    n = [int(r[0].replace(",", "")) for r in rows]
    pct = lambda v: float(v.rstrip("%"))  # noqa: E731
    fig, (ax, bx) = d2d.figure(height=2.0, width=1.0, ncols=2)
    ax.plot(n, [pct(r[2]) for r in rows], color=d2d.MUTED, marker="o", ms=3.5, lw=d2d.LINE_PT, ls="--", label="Neyman least squares")
    ax.plot(n, [pct(r[3]) for r in rows], color=d2d.PART, marker="s", ms=3.5, lw=d2d.LINE_PT * 1.4, label="Poisson likelihood")
    ax.axhline(0, color=d2d.INK, lw=0.5)
    ax.set_xscale("log")
    ax.set_xlabel("counts in the peak")
    ax.set_ylabel("bias of the fitted area, %")
    ax.legend(loc="lower right", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    bx.plot(n, [float(r[6]) for r in rows], color=d2d.MUTED, marker="o", ms=3.5, lw=d2d.LINE_PT, ls="--", label="Neyman")
    bx.plot(n, [float(r[7]) for r in rows], color=d2d.PART, marker="s", ms=3.5, lw=d2d.LINE_PT * 1.4, label="Poisson")
    bx.axhline(1, color=d2d.INK, lw=0.5)
    bx.set_xscale("log")
    bx.set_ylim(0.6, 1.7)
    bx.set_xlabel("counts in the peak")
    bx.set_ylabel("SD of the area's pull")
    bx.text(150, 1.6, "1 when the reported errors are right", fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED, va="top")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
