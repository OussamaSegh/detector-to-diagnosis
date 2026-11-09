# SPDX-License-Identifier: MIT
"""Figure for Chapter 31: the QC report on five runs of the simulator's point source: the energy
resolution and the coincidence time resolution of each seed with its reported error, against what
the simulator was made to do. From section 3 of measurements/ch31/analysis.txt.

    python3 book/tools/figures.py build book/figures/plots/ch31/qc.py screen 7 pdf measurements/ch31/analysis.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch31/analysis.txt"


def pm(v):
    a, b = v.split("±")
    return float(a), float(b)


def main(dst):
    text = SRC.read_text().split("## 3.")[1].split("## 4.")[0]
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")][1:]
    seeds = [int(r[0]) for r in rows]
    fig, (ax, bx) = d2d.figure(height=1.9, width=1.0, ncols=2)
    for a, k, truth, lab, c in ((ax, 4, 12.0, "FWHM / E, %", d2d.PART), (bx, 5, 300.0, "CTR FWHM, ps", d2d.CAT[0])):
        v = [pm(r[k]) for r in rows]
        a.errorbar(seeds, [x[0] for x in v], yerr=[x[1] for x in v], fmt="o", color=c, ms=4, capsize=2.5, lw=0.9)
        a.axhline(truth, color=d2d.INK, lw=0.7, ls="--")
        a.text(5.4, truth, "simulator", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, va="bottom", ha="right")
        a.set_xticks(seeds)
        a.set_xlabel("seed")
        a.set_ylabel(lab)
        a.set_xlim(0.5, 5.5)
    ax.set_ylim(11.85, 12.1)
    bx.set_ylim(298, 306)
    bx.text(0.7, 305.2, "3 ps above 300: the depth of interaction", fontsize=d2d.FONT_PT - 1.2, color=d2d.CAT[0])
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
