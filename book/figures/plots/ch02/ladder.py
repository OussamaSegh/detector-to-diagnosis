# SPDX-License-Identifier: MIT
"""Figure for Chapter 2: load latency by working set on the book's VM, from the chapter's table
(bm_latency, pointer chase, mean of three runs; Xeon at 2.30 GHz).

    python3 book/tools/figures.py build book/figures/plots/ch02/ladder.py screen 1 pdf
"""
import sys

import d2d

ROWS = [("16 KiB", "L1", 1.7, 4), ("512 KiB", "L2", 5.9, 13), ("8 MiB", "L3", 36, 83),
        ("64 MiB", "far L3, DRAM", 138, 320), ("1 GiB", "DRAM + TLB", 204, 470)]


def main(dst):
    fig, ax = d2d.figure(height=2.2, width=0.85)
    y = list(range(len(ROWS)))[::-1]
    for k, (ws, where, ns, cyc) in enumerate(ROWS):
        c = d2d.tint(d2d.PART, 0.35 + 0.65 * k / (len(ROWS) - 1))
        ax.barh(y[k], ns, color=c, height=0.62, edgecolor=d2d.PART, linewidth=0.6)
        ax.text(ns * 1.12, y[k], f"{ns:g} ns  (about {cyc} cycles)", va="center",
                fontsize=d2d.FONT_PT - 0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{ws}: {w}" for ws, w, _, _ in ROWS])
    ax.set_xscale("log")
    ax.set_xlim(1, 2500)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("latency per dependent load (ns, log scale)")
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
