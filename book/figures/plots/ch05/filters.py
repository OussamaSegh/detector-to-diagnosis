# SPDX-License-Identifier: MIT
"""Figure for Chapter 5: the energy filter kernels against the share of singles that pass,
on random input, from measurements/ch05/bm_energy_filter.json (medians, batches of 4,096,
a different batch every iteration).

    python3 book/tools/figures.py build book/figures/plots/ch05/filters.py screen 1 pdf
"""
import json
import os
import sys

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch05/bm_energy_filter.json")
KERNELS = (("branchy", 3, "o", "-"), ("branchless", 0, "s", "--"), ("AVX2", 2, "^", "-."), ("AVX-512", 4, "D", ":"))


def main(dst):
    rows = {}
    for b in json.load(open(SRC, encoding="utf-8"))["benchmarks"]:
        if b["name"].endswith("_median"):
            k, a, p, n = b["name"].split("/")[1:5]
            rows[(int(k), int(a), int(p), n.split("_")[0])] = b["items_per_second"] / 1e6
    fig, ax = d2d.figure(height=2.3, width=0.62)
    acc = [10, 50, 90]
    for k, (name, c, m, ls) in enumerate(KERNELS):
        ax.plot(acc, [rows[(k, a, 0, "4096")] for a in acc], marker=m, linestyle=ls,
                color=d2d.PART if k == 0 else d2d.CAT[c], label=name)
    ax.annotate("branchy, same batch\nevery iteration: 1,028", xy=(50, rows[(0, 50, 2, "4096")]), xytext=(55, 600),
                fontsize=d2d.FONT_PT - 0.8, arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.7})
    ax.plot([50], [rows[(0, 50, 2, "4096")]], "x", color=d2d.INK)
    ax.set_xticks(acc)
    ax.set_xticklabels([f"{a}%" for a in acc])
    ax.set_xlabel("singles inside the window")
    ax.set_ylabel("M singles per second")
    ax.set_ylim(0, 1150)
    ax.legend(loc="lower right", ncol=2)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
