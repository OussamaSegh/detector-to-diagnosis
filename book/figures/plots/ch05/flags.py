# SPDX-License-Identifier: MIT
"""Figure for Chapter 5: five builds of the same code, as speed ratios to -O2, from
measurements/ch05/flags/summary.md (medians of ten interleaved runs).

    python3 book/tools/figures.py build book/figures/plots/ch05/flags.py screen 1 pdf
"""
import os
import re
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch05/flags/summary.md")
NAMES = {"BM_DecodePacked/65536": "decode", "BM_EnergyFilter/0/50/0/4096": "filter, branchy",
         "BM_EnergyFilter/1/50/0/4096": "filter, branchless", "BM_SortFunctionPointer/4096/0": "sort, function pointer",
         "BM_SortLambda/4096/0": "sort, lambda", "BM_Pipeline/4096/64/real_time": "pipeline"}
COLS = ["-O3", "-march=native", "LTO", "PGO"]


def read():
    rows = {}
    for line in open(SRC, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] in NAMES:
            rows[NAMES[cells[0]]] = [float(re.search(r"([\d.]+)x", c).group(1)) for c in cells[2:6]]
    return rows


def main(dst):
    rows = read()
    order = [n for n in NAMES.values() if n in rows]
    m = np.array([rows[n] for n in order])
    fig, ax = d2d.figure(height=2.3, width=0.7)
    cmap = LinearSegmentedColormap.from_list("div", [d2d.CAT[3], "#FFFFFF", d2d.PART])
    ax.imshow(np.log(m), cmap=cmap, norm=TwoSlopeNorm(0, -1.3, 1.3), aspect="auto")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, f"{m[i, j]:.2f}x", ha="center", va="center", fontsize=d2d.FONT_PT - 0.4,
                    color="white" if abs(np.log(m[i, j])) > 0.7 else d2d.INK,
                    fontweight="bold" if abs(m[i, j] - 1) >= 0.1 else "normal")
    ax.set_xticks(range(len(COLS)))
    ax.set_xticklabels(COLS)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("speed relative to -O2 (bold: 10% or more either way)")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
