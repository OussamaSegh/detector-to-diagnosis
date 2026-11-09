# SPDX-License-Identifier: MIT
"""Figure for Chapter 4: minidaq_jitter's wake-up latency percentiles, from the chapter's table
(15 s, 200 us period, pinned, memory locked; idle and under stress-ng).

    python3 book/tools/figures.py build book/figures/plots/ch04/jitter.py screen 1 pdf
"""
import sys

import d2d

P = ["p50", "p99", "p99.9", "p99.99", "max"]
ROWS = [("idle, SCHED_OTHER", [60.4, 108.5, 1040, 2007, 2465], 0, "o", "-"),
        ("idle, SCHED_FIFO 80", [10.4, 29.3, 774, 8389, 9623], 2, "s", "--"),
        ("load, SCHED_OTHER", [67, 7668, 13238, 24642, 25790], 3, "^", "-."),
        ("load, SCHED_FIFO 80", [17, 51.5, 2720, 12255, 13411], None, "D", "-")]


def main(dst):
    fig, ax = d2d.figure(height=2.5, width=0.7)
    for name, v, c, m, ls in ROWS:
        ax.plot(range(len(P)), v, marker=m, linestyle=ls, color=d2d.PART if c is None else d2d.CAT[c],
                label=name, linewidth=1.4 if c is None else 1.1)
    ax.annotate("p99: 7.7 ms against 52 µs", xy=(1, 7668), xytext=(1.25, 30000), fontsize=d2d.FONT_PT - 0.6,
                arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.7})
    ax.set_xticks(range(len(P)))
    ax.set_xticklabels(P)
    ax.set_yscale("log")
    ax.set_ylim(5, 80000)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_ylabel("wake-up latency (µs)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
