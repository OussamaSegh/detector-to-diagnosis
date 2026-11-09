# SPDX-License-Identifier: MIT
"""Figure for Chapter 7: the cost of hardening, every run of every build, relative to the median
of the unhardened build (measurements/ch07, five rounds, GCC 13.3 -O2).

    python3 book/tools/figures.py build book/figures/plots/ch07/hardcost.py screen 1 pdf measurements/ch07
"""
import json
import pathlib
import statistics
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch07"
BENCH = [("decode", "BM_DecodePacked/4194304", "decode"), ("filter", "BM_EnergyFilter/1/50/0/4096", "filter, branchless"),
         ("filter", "BM_EnergyFilter/2/50/0/4096", "filter, AVX2"), ("sort", "BM_SortLambda/4096/0", "sort, std::sort"),
         ("hist", "BM_HistogramRecord", "histogram record()"), ("pipe", "BM_Pipeline/4096/64/real_time", "whole pipeline")]
BUILDS = [("hard-off", "none", d2d.MUTED, "o"), ("release", "distro", d2d.CAT[0], "s"), ("hardened", "hardened", d2d.PART, "D")]


def runs(build, file, name):
    out = []
    for i in range(1, 6):
        for b in json.loads((SRC / f"{build}.{file}.{i}.json").read_text())["benchmarks"]:
            if b["name"] == name:
                out.append(b["real_time"])
    return out


def main(dst):
    fig, ax = d2d.figure(height=2.6, width=0.85)
    for k, (file, name, label) in enumerate(BENCH):
        base = statistics.median(runs("hard-off", file, name))
        for j, (build, blabel, c, m) in enumerate(BUILDS):
            v = [100 * (x / base - 1) for x in runs(build, file, name)]
            y = len(BENCH) - 1 - k + (1 - j) * 0.24
            ax.scatter(v, [y] * len(v), color=c, marker=m, s=14, alpha=0.85, linewidths=0,
                       label=blabel if k == 0 else None, zorder=3)
            ax.plot([statistics.median(v)] * 2, [y - 0.1, y + 0.1], color=c, linewidth=1.6, zorder=4)
    ax.axvline(0, color=d2d.INK, linewidth=0.7)
    ax.axvspan(-10, 10, color=d2d.tint(d2d.MUTED, 0.15), zorder=0, linewidth=0)
    ax.text(9.5, len(BENCH) - 0.45, "±10%: run-to-run noise on this VM", ha="right", va="bottom", fontsize=d2d.FONT_PT - 0.8)
    ax.set_yticks(range(len(BENCH)))
    ax.set_yticklabels([b[2] for b in reversed(BENCH)])
    ax.set_ylim(-0.6, len(BENCH) - 0.1)
    ax.set_xlabel("time against the median of the unhardened build (%)")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=d2d.FONT_PT - 0.6, ncol=3, frameon=False, bbox_to_anchor=(1, 1.0))
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
