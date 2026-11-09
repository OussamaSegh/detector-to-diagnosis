# SPDX-License-Identifier: MIT
"""Figure for Chapter 3: hand-off rates of the queue variants, from the chapter's table
(bm_spsc, ten repetitions on the book's VM; bar = median, line = min to max).

    python3 book/tools/figures.py build book/figures/plots/ch03/spsc.py screen 1 pdf
"""
import sys

import d2d

ROWS = [("std::mutex + std::deque", 4.9, 5.2, 5.6), ("ring, seq_cst", 5.5, 7.1, 7.6),
        ("ring, acquire/release", 36.4, 61.7, 140.4), ("SpscRing (cached indices)", 39.8, 51.6, 63.7),
        ("MpmcQueue, 1 producer", 25.7, 28.7, 35.0), ("SpscRing, batches of 16", 142.3, 159.0, 227.6),
        ("SpscRing, batches of 256", 363.7, 386.8, 462.7)]


def main(dst):
    fig, ax = d2d.figure(height=2.5, width=0.9)
    n = len(ROWS)
    for k, (name, lo, med, hi) in enumerate(ROWS):
        y = n - 1 - k
        c = d2d.PART if "batches" in name else d2d.tint(d2d.PART, 0.45)
        ax.barh(y, med, color=c, height=0.6)
        ax.plot([lo, hi], [y, y], color=d2d.INK, linewidth=0.9)
        ax.plot([lo, hi], [y, y], "|", color=d2d.INK, markersize=6)
        ax.text(hi * 1.15, y, f"{med:g}", va="center", fontsize=d2d.FONT_PT - 0.6)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in reversed(ROWS)])
    ax.set_xscale("log")
    ax.set_xlim(3, 1200)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("million items per second (log scale; bar median, line min to max)")
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
