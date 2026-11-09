# SPDX-License-Identifier: MIT
"""Figure for Chapter 5: the performance budget, from the chapter's table (docs/performance-budget.md):
measured nanoseconds per single for each stage against what 10 M and 30 M singles per second allow.

    python3 book/tools/figures.py build book/figures/plots/ch05/budget.py screen 1 pdf
"""
import sys

import d2d

ROWS = [("energy spectrum", 0.44, 0.44), ("energy window", 1.1, 1.1), ("decode", 3.0, 3.0),
        ("sort (4,096)", 7.4, 8.5), ("whole pipeline", 11.6, 11.6)]


def main(dst):
    fig, ax = d2d.figure(height=2.1, width=0.8)
    for k, (name, lo, hi) in enumerate(ROWS):
        c = d2d.PART if name == "whole pipeline" else d2d.tint(d2d.PART, 0.5)
        ax.barh(k, hi, color=c, height=0.6)
        ax.text(hi * 1.12, k, f"{lo:g}" if lo == hi else f"{lo:g} to {hi:g}", va="center", fontsize=d2d.FONT_PT - 0.6)
    for v, label, ls, ha in ((100, "budget at 10 M/s: 100 ns", "--", "left"), (33.3, "at 30 M/s: 33 ns", ":", "right")):
        ax.axvline(v, color=d2d.SEM["mistakes"], linestyle=ls, linewidth=1.1)
        ax.text(v * (1.06 if ha == "left" else 0.94), len(ROWS) - 0.45, label, fontsize=d2d.FONT_PT - 0.8,
                va="bottom", ha=ha)
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([r[0] for r in ROWS])
    ax.set_xscale("log")
    ax.set_xlim(0.2, 600)
    ax.set_ylim(-0.6, len(ROWS) + 0.1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("ns per single, measured (one core per stage)")
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
