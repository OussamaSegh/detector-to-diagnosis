# SPDX-License-Identifier: MIT
"""Figure for Chapter 4: MiniDAQ's end-to-end latency by profile, idle and under load, from the
chapter's table (minidaq_latency, 10 M words/s for 20 s, medians of three runs).

    python3 book/tools/figures.py build book/figures/plots/ch04/endtoend.py screen 1 pdf
"""
import sys

import numpy as np

import d2d

P = ["p50", "p99", "p99.9", "max"]
ROWS = [("idle", "default", [0.78, 1.8, 5.8, 12.5]), ("idle", "rt-pin", [0.75, 2.2, 5.8, 12.2]),
        ("idle", "rt-fifo", [0.70, 44, 50, 53]), ("load", "default", [2835, 4765, 4918, 4918]),
        ("load", "rt-pin", [3221, 7315, 7416, 7420]), ("load", "rt-fifo", [5.6, 52, 61, 69])]
STYLE = {"default": (0, "o"), "rt-pin": (3, "s"), "rt-fifo": (None, "D")}


def main(dst):
    fig, axes = d2d.figure(height=2.4, ncols=2, sharey=True)
    for ax, load in zip(axes, ("idle", "load")):
        for l, prof, v in ROWS:
            if l != load:
                continue
            c, m = STYLE[prof]
            ax.plot(range(4), v, marker=m, color=d2d.PART if c is None else d2d.CAT[c], label=prof,
                    linestyle="-" if c is None else "--")
        ax.set_title(load if load == "idle" else "under stress-ng load")
        ax.set_xticks(range(4))
        ax.set_xticklabels(P)
        ax.set_yscale("log")
    axes[0].set_ylabel("end-to-end latency (ms)")
    axes[0].yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    axes[1].legend(loc="lower right")
    axes[1].text(3, 1500, "default and rt-pin fall behind:\nseconds, and data dropped", ha="right", va="top",
                 fontsize=d2d.FONT_PT - 0.8)
    axes[0].set_ylim(0.3, 20000)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
