# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: heap merger against slice merger, by number of boards, from
measurements/ch10/bench_slice_merge.txt (medians of five repetitions).

    python3 book/tools/figures.py build book/figures/plots/ch10/slices.py screen 2 pdf
"""
import os
import re
import sys

import numpy as np

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch10/bench_slice_merge.txt")


def read():
    out = {}
    for line in open(SRC, encoding="utf-8"):
        m = re.match(r"BM_(Heap|Slices)/(\d+)_median\s.*items_per_second=([\d.]+)M/s", line)
        if m:
            out[(m.group(1), int(m.group(2)))] = float(m.group(3))
    return out


def main(dst):
    data = read()
    boards = sorted({b for _, b in data})
    x = np.arange(len(boards))
    fig, ax = d2d.figure(height=2.3, width=0.62)
    for k, (kind, label, c, hatch) in enumerate((("Heap", "heap merger", d2d.CAT[0], ""),
                                                ("Slices", "slice merger", d2d.CAT[3], "///"))):
        v = [data[(kind, b)] for b in boards]
        bars = ax.bar(x + (k - 0.5) * 0.38, v, width=0.36, color=d2d.tint(c, 0.45), edgecolor=c,
                      hatch=hatch, label=label, linewidth=0.8)
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.8, f"{val:.1f}", ha="center",
                    fontsize=d2d.FONT_PT - 0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{b} boards" for b in boards])
    ax.set_ylabel("million singles per second")
    ax.set_ylim(0, 56)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
