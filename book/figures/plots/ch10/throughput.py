# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: the sorter's throughput against the 30 M singles per second target,
from measurements/ch10/bench_sorter.txt (means of five repetitions). Each bar is the singles
offered per second; its dark part is the share inside the energy window (in_window), which is
what the target counts.

    python3 book/tools/figures.py build book/figures/plots/ch10/throughput.py screen 2 pdf
"""
import os
import re
import sys

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch10/bench_sorter.txt")
TARGET = 30.0
ROWS = [
    ("BM_Sorter/0/0/0", "fixed, kill all,\nno delayed window"),
    ("BM_Sorter/0/1/0", "fixed, kill all"),
    ("BM_Sorter/1/1/0", "fixed, take all goods"),
    ("BM_Sorter/2/1/0", "fixed, winner of goods"),
    ("BM_Sorter/3/1/0", "fixed, only one good"),
    ("BM_Sorter/0/1/1", "fixed, kill all, 120 mm FOV"),
    ("BM_SorterPerSingle", "per single, kill all"),
]


def read():
    out = {}
    for line in open(SRC, encoding="utf-8"):
        m = re.match(r"(\S+)_mean\s.*in_window=([\d.]+).*items_per_second=([\d.]+)M/s", line)
        if m:
            out[m.group(1)] = (float(m.group(3)), float(m.group(2)))
    return out


def main(dst):
    data = read()
    fig, ax = d2d.figure(height=2.6)
    for k, (key, label) in enumerate(ROWS):
        total, frac = data[key]
        y = len(ROWS) - 1 - k
        inside = total * frac
        ax.barh(y, total, color=d2d.tint(d2d.PART, 0.3), height=0.62, linewidth=0)
        ax.barh(y, inside, color=d2d.PART, height=0.62, linewidth=0)
        ax.text(total + 1.0, y, f"{total:.1f} M offered", va="center", fontsize=d2d.FONT_PT - 0.6)
        ax.text(inside - 1.0, y, f"{inside:.1f} M", va="center", ha="right", color="white",
                fontsize=d2d.FONT_PT - 0.6, fontweight="bold")
    ax.axvline(TARGET, color=d2d.SEM["mistakes"], linestyle="--", linewidth=1.2)
    ax.text(TARGET + 0.8, len(ROWS) - 0.45, "target: 30 M per second inside the energy window",
            va="bottom", fontsize=d2d.FONT_PT - 0.6, color=d2d.INK)
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([r[1] for r in reversed(ROWS)])
    ax.set_xlim(0, 105)
    ax.set_ylim(-0.6, len(ROWS) + 0.1)
    ax.set_axisbelow(True)
    ax.set_xlabel("million singles per second (dark: inside the energy window)")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
