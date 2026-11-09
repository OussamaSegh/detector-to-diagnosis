# SPDX-License-Identifier: MIT
"""Figure for Chapter 23: the receiving thread's cost per datagram, recv against recvmmsg batches,
for full-size MDQ-R1 and jumbo datagrams (min, median, max of 10 repetitions), from
measurements/ch23/receive_cost.txt.

    python3 book/tools/figures.py build book/figures/plots/ch23/cost.py screen 5 pdf measurements/ch23/receive_cost.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch23/receive_cost.txt"
ROW = re.compile(r"^\| (recv|recvmmsg, \d+) \| ([\d,]+) B \| (\d+) / (\d+) / (\d+) \|")


def main(dst):
    rows = [(m.group(1), m.group(2), *map(int, m.group(3, 4, 5))) for m in map(ROW.match, SRC.read_text().splitlines()) if m]
    calls = list(dict.fromkeys(r[0] for r in rows))
    sizes = list(dict.fromkeys(r[1] for r in rows))
    fig, ax = d2d.figure(height=1.9, width=0.7)
    for j, size in enumerate(sizes):
        c = d2d.PART if j == 0 else d2d.CAT[0]
        for i, call in enumerate(calls):
            r = next(r for r in rows if r[0] == call and r[1] == size)
            x = i + (j - 0.5) * 0.28
            ax.plot([x, x], [r[2], r[4]], color=d2d.tint(c, 0.5), linewidth=2.2, solid_capstyle="round")
            ax.scatter(x, r[3], color=c, marker=d2d.MARKERS[j], s=22, zorder=3,
                       label=f"{size} B datagram" if i == 0 else None)
    ax.set_xticks(range(len(calls)))
    ax.set_xticklabels(calls)
    ax.set_ylabel("ns per datagram")
    ax.set_ylim(0, 1000)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1, frameon=False)
    ax.text(3.4, 120, "bars: min to max of 10 repetitions; marker: median", ha="right", fontsize=d2d.FONT_PT - 1.3, color=d2d.MUTED)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
