# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: how busy each software stage is against the singles rate, from
measurements/ch11/bottleneck.txt (two runs per activity), with a line through the origin
fitted to each stage: where it reaches 100% is the stage's capacity.

    python3 book/tools/figures.py build book/figures/plots/ch11/bottleneck.py screen 2 pdf
"""
import os
import sys

import numpy as np

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch11/bottleneck.txt")
STAGES = (("pair", 6, 0), ("sort", 5, 1), ("decode", 4, 2))


def read():
    rows = []
    for line in open(SRC, encoding="utf-8"):
        f = line.split()
        if len(f) == 9 and f[0].isdigit():
            rows.append([float(v) for v in f])
    return np.array(rows)


def main(dst):
    d = read()
    rate = d[:, 1] / 1e6
    fig, ax = d2d.figure(height=2.5, width=0.75)
    x = np.linspace(0, 110, 50)
    for name, col, k in STAGES:
        busy = d[:, col]
        slope = (rate @ busy) / (rate @ rate)
        cap = 100 / slope
        c = d2d.PART if name == "pair" else d2d.CAT[k]
        ax.plot(x, slope * x, color=c, linestyle=d2d.DASHES[1], linewidth=0.9)
        ax.plot(rate, busy, d2d.MARKERS[k], color=c, linestyle="none")
        if cap < 110:
            ax.plot([cap], [100], "o", markersize=7, markerfacecolor="white", markeredgecolor=c)
            ax.annotate(f"{name}: full at {cap:.0f} M", xy=(cap, 100),
                        xytext=(cap - 4, 106) if name == "pair" else (cap, 106),
                        ha="right" if name == "pair" else "center", color=d2d.INK, fontsize=d2d.FONT_PT - 0.6, fontweight="bold")
        else:
            ax.text(108, slope * 108 + 2, f"{name}: about {cap:.0f} M", ha="right", va="bottom",
                    fontsize=d2d.FONT_PT - 0.6, fontweight="bold")
    ax.axhline(100, color=d2d.MUTED, linewidth=0.7)
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 118)
    ax.set_xlabel("singles per second offered (millions)")
    ax.set_ylabel("busy (%)")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
