# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: what the multiples policy does to the randoms fraction
and to the delayed-window estimate, from measurements/ch10/validation.txt (the
table with the sector and field-of-view cuts).

    python3 book/tools/figures/ch10_policies.py book/src/img/ch10-policies.png
"""
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "../../../measurements/ch10/validation.txt")
STYLE = {
    "kill_all": ("#1f5fa8", "o", "kill all"),
    "take_all_goods": ("#c0392b", "s", "take all goods"),
    "take_winner_of_goods": ("#7a9a3a", "^", "winner of goods"),
    "keep_if_only_one_good": ("#e08a2b", "D", "only one good"),
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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.9), dpi=200)
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
    ax1.set_ylabel("randoms in the prompts (%)", fontsize=8)
    ax1.set_title("randoms fraction", fontsize=9)
    ax1.legend(fontsize=7, frameon=False)
    ax2.axhline(0, color="black", linewidth=0.6)
    ax2.set_ylabel("delayed vs true randoms (%)", fontsize=8)
    ax2.set_title("delayed-window estimate error", fontsize=9)
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1])
