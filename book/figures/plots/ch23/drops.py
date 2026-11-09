# SPDX-License-Identifier: MIT
"""Figure for Chapter 23: where the datagrams of a burst went, every run of every buffer size:
delivered, dropped with a sequence gap, and dropped at the tail (socket drops minus gaps). From
measurements/ch23/drop_accounting.txt.

    python3 book/tools/figures.py build book/figures/plots/ch23/drops.py screen 5 pdf measurements/ch23/drop_accounting.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch23/drop_accounting.txt"
ROW = re.compile(r"^\| (burst, 5 MBq, (64 KiB|256 KiB|1 MiB|4 MiB)) \| [\d,]+ \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \|")


def num(s):
    return int(s.replace(",", ""))


def main(dst):
    runs, run = [], 0
    for line in SRC.read_text().splitlines():
        if line.startswith("## Run"):
            run = int(line.split()[-1])
        m = ROW.match(line)
        if m:
            runs.append((m.group(2), run, num(m.group(3)), num(m.group(4)), num(m.group(5)), num(m.group(6))))
    sizes = ["64 KiB", "256 KiB", "1 MiB", "4 MiB"]
    fig, ax = d2d.figure(height=2.3, width=0.85)
    x, ticks, labels = 0, [], []
    for s in sizes:
        for size, r, sent, delivered, gaps, drops in [t for t in runs if t[0] == s]:
            tail = drops - gaps
            ax.bar(x, delivered, color=d2d.CAT[2], width=0.8, label="delivered" if x == 0 else None)
            ax.bar(x, gaps, bottom=delivered, color=d2d.CAT[1], hatch="////", edgecolor="white", linewidth=0.3, width=0.8,
                   label="dropped, seen as a sequence gap" if x == 0 else None)
            ax.bar(x, tail, bottom=delivered + gaps, color=d2d.SEM["mistakes"], hatch="....", edgecolor="white", linewidth=0.3,
                   width=0.8, label="dropped at the tail: no gap, only the socket's count" if x == 0 else None)
            ax.text(x, -500, f"run {r}", ha="center", va="top", fontsize=d2d.FONT_PT - 1.6, color=d2d.MUTED)
            x += 1
        ticks.append(x - 2)
        labels.append(s)
        x += 0.8
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.tick_params(axis="x", length=0, pad=12)
    ax.set_xlabel("receive buffer granted (burst of 12,291 datagrams, three runs each)")
    ax.set_ylabel("datagrams")
    ax.set_ylim(0, 12800)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=d2d.FONT_PT - 1, frameon=False, ncol=2)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
