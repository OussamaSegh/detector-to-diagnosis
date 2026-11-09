# SPDX-License-Identifier: MIT
"""Figure for Chapter 2: AoS against SoA over 100 M singles from DRAM, from the chapter's table
(bm_layout, mean of three repetitions on the book's VM).

    python3 book/tools/figures.py build book/figures/plots/ch02/layout.py screen 1 pdf
"""
import sys

import numpy as np

import d2d

ROWS = [("sum energies", 508, 1190), ("gate on all fields", 362, 625)]


def main(dst):
    fig, ax = d2d.figure(height=2.0, width=0.6)
    x = np.arange(len(ROWS))
    for k, (name, c, h) in enumerate((("AoS: 16 bytes per single", d2d.CAT[0], ""),
                                      ("SoA: only the fields used", d2d.CAT[2], "///"))):
        v = [r[1 + k] for r in ROWS]
        bars = ax.bar(x + (k - 0.5) * 0.36, v, 0.34, color=d2d.tint(c, 0.5), edgecolor=c, hatch=h,
                      label=name, linewidth=0.8)
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 25, f"{val:,}", ha="center", fontsize=d2d.FONT_PT - 0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in ROWS])
    ax.set_ylabel("M singles per second")
    ax.set_ylim(0, 1450)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
