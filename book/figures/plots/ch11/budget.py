# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: the throughput budget. The singles rate the front end delivers
against the activity (measurements/ch11/countrate.txt), without dead time and with the 1 us
block dead time and pile-up, against the capacity of each stage.

    python3 book/tools/figures.py build book/figures/plots/ch11/budget.py screen 2 pdf
"""
import os
import sys

import matplotlib.ticker

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch11/countrate.txt")
CAPS = ((148, "one 10 GbE link"), (96, "sort stage"), (70, "pair stage (sorter)"), (14.8, "one Gigabit link"))


def read():
    out, section = {}, None
    for line in open(SRC, encoding="utf-8"):
        if line.startswith("== "):
            section = line[3:].strip()
            out[section] = ([], [])
            continue
        f = line.split()
        if section and f and f[0].isdigit():
            out[section][0].append(float(f[0]))
            out[section][1].append(float(f[2]) / 1e6)
    return out


def main(dst):
    d = read()
    fig, ax = d2d.figure(height=2.7, width=0.8)
    for k, (key, label) in enumerate((("no dead time", "no dead time"),
                                      ("non-paralyzable 1 us per block, pile-up", "1 µs per block, pile-up"))):
        x, y = d[key]
        ax.plot(x, y, marker=d2d.MARKERS[k], color=d2d.CAT[0] if k == 0 else d2d.CAT[3],
                linestyle=d2d.DASHES[k], label=label)
    for v, name in CAPS:
        c = d2d.PART if "pair" in name else d2d.MUTED
        ax.axhline(v, color=c, linewidth=1.0 if "pair" in name else 0.7, linestyle=(0, (4, 2)))
        below = "pair" in name
        ax.text(5.3, v * (0.93 if below else 1.06), f"{name}, {v:g} M", fontsize=d2d.FONT_PT - 0.8,
                color=d2d.INK, va="top" if below else "bottom")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(5, 1000)
    ax.set_ylim(0.6, 260)
    ax.set_xlabel("activity (MBq)")
    ax.set_ylabel("singles per second (millions)")
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500, 1000])
    ax.set_yticks([1, 2, 5, 10, 20, 50, 100, 200])
    ax.minorticks_off()
    ax.legend(loc="lower right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
