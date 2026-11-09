# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: what the multiples policy does to the randoms fraction
and to the delayed-window estimate, from measurements/ch10/validation.txt (the
table with the sector and field-of-view cuts).

    python3 book/tools/figures.py build book/figures/plots/ch10/policies.py screen 2 pdf
"""
import os
import re
import sys

import matplotlib.pyplot as plt

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch10/validation.txt")
STYLE = {
    "kill_all": (d2d.CAT[0], "o", "kill all"),
    "take_all_goods": (d2d.CAT[3], "s", "take all goods"),
    "take_winner_of_goods": (d2d.CAT[2], "^", "winner of goods"),
    "keep_if_only_one_good": (d2d.CAT[1], "D", "only one good"),
}


def read_table():
    rows = {}
    in_cut_table = False
    for line in open(SRC, encoding="utf-8"):
        if line.startswith("== "):
            in_cut_table = "field of view" in line
            continue
        m = re.match(r"\s*(\d+) (\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([+-][\d.]+) ±\s*([\d.]+)\s+([\d.]+)", line)
        if in_cut_table and m:
            mbq, policy = int(m.group(1)), m.group(2)
            rows.setdefault(policy, []).append(
                (mbq, float(m.group(8)), float(m.group(9)), float(m.group(10))))
    return rows


def main(dst):
    rows = read_table()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.9))
    for i, (policy, (color, marker, label)) in enumerate(STYLE.items()):
        pts = rows[policy]
        x = [p[0] for p in pts]
        ax1.plot(x, [p[3] for p in pts], marker=marker, color=color, markersize=3.5, linewidth=1.0, label=label)
        shift = 1.0 + 0.04 * (i - 1.5)  # spread the error bars so they do not hide each other
        ax2.errorbar([v * shift for v in x], [p[1] for p in pts], yerr=[p[2] for p in pts], marker=marker,
                     color=color, markersize=3.5, linewidth=1.0, capsize=2, elinewidth=0.7)
    for ax in (ax1, ax2):
        ax.set_xscale("log")
        ax.set_xticks([1, 5, 10, 20, 40])
        ax.set_xticklabels(["1", "5", "10", "20", "40"])
        ax.set_xlabel("activity (MBq)")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax1.set_ylabel("randoms in the prompts (%)")
    ax1.set_title("randoms fraction")
    ax1.legend(frameon=False)
    ax2.axhline(0, color=d2d.INK, linewidth=0.6)
    ax2.set_ylabel("delayed vs true randoms (%)")
    ax2.set_title("delayed-window estimate error")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
