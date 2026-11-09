# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: NECR (k = 1) against the coincidence time window and
the lower energy threshold, at 30 and 100 MBq, from measurements/ch11/windows.txt.

    python3 book/tools/figures.py build book/figures/plots/ch11/windows.py screen 2 pdf
"""
import os
import re
import sys

import matplotlib.pyplot as plt

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch11/windows.txt")
COLORS = {30: d2d.CAT[0], 100: d2d.CAT[3]}


def read_table():
    """(MBq, "time" or "energy") -> list of (x, necr1)."""
    rows, key = {}, None
    for line in open(SRC, encoding="utf-8"):
        m = re.match(r"== (\d+) MBq, (time|lower)", line)
        if m:
            key = (int(m.group(1)), "time" if m.group(2) == "time" else "energy")
            rows[key] = []
            continue
        m = re.match(r"\s*([\d.]+) (ns|keV)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)", line)
        if key and m:
            rows[key].append((float(m.group(1)), float(m.group(8))))
    return rows


def main(dst):
    rows = read_table()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.6))
    for (mbq, color), m, ls in zip(COLORS.items(), ("o", "s"), ("-", "--")):
        for ax, kind in ((ax1, "time"), (ax2, "energy")):
            pts = rows[(mbq, kind)]
            ax.plot([p[0] for p in pts], [p[1] / 1e3 for p in pts], marker=m, markersize=3.2, color=color,
                    linestyle=ls, linewidth=1.0, label=f"{mbq} MBq")
    ax1.axvline(4, color=d2d.MUTED, linewidth=0.6, linestyle=":")
    ax2.axvline(435, color=d2d.MUTED, linewidth=0.6, linestyle=":")
    ax1.set_xlabel("time window (ns)")
    ax1.set_title("time window (435 to 585 keV)")
    ax2.set_xlabel("lower energy threshold (keV)")
    ax2.set_title("energy window (4 ns, upper 585 keV)")
    for ax in (ax1, ax2):
        ax.set_ylabel("NECR, k = 1 (k/s)")
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax1.legend(frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
