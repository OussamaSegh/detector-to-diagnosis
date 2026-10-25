# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: NECR (k = 1) against the coincidence time window and
the lower energy threshold, at 30 and 100 MBq, from measurements/ch11/windows.txt.

    python3 book/tools/figures/ch11_windows.py book/src/img/ch11-windows.png
"""
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "../../../measurements/ch11/windows.txt")
COLORS = {30: "#1f5fa8", 100: "#c0392b"}


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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.6), dpi=200)
    for mbq, color in COLORS.items():
        for ax, kind in ((ax1, "time"), (ax2, "energy")):
            pts = rows[(mbq, kind)]
            ax.plot([p[0] for p in pts], [p[1] / 1e3 for p in pts], marker="o", markersize=3, color=color,
                    linewidth=1.0, label=f"{mbq} MBq")
    ax1.axvline(4, color="gray", linewidth=0.6, linestyle=":")
    ax2.axvline(435, color="gray", linewidth=0.6, linestyle=":")
    ax1.set_xlabel("time window (ns)", fontsize=8)
    ax1.set_title("time window (435 to 585 keV)", fontsize=9)
    ax2.set_xlabel("lower energy threshold (keV)", fontsize=8)
    ax2.set_title("energy window (4 ns, upper 585 keV)", fontsize=9)
    for ax in (ax1, ax2):
        ax.set_ylabel("NECR, k = 1 (k/s)", fontsize=8)
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax1.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1])
