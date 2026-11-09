# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: the two dead-time models. Left: recorded against true
rate per unit, in units of 1 / tau. Right: the share of singles lost against
activity, simulated (measurements/ch11/countrate.txt) and from the models with
the average singles rate per block.

    python3 book/tools/figures.py build book/figures/plots/ch11/deadtime.py screen 2 pdf
"""
import math
import os
import sys

import matplotlib.pyplot as plt

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch11/countrate.txt")
BLOCKS = 72
TAU = 1e-6
NP, P = d2d.CAT[3], d2d.CAT[2]


def read_lost():
    """model -> list of (MBq, singles in per second, lost %) from the dead-time tables."""
    rows, section, ideal = {}, None, {}
    for line in open(SRC, encoding="utf-8"):
        if line.startswith("== "):
            section = line[3:].split()[0]  # "no", "non-paralyzable" or "paralyzable"
            rows[section] = []
            continue
        f = line.split()
        if section and f and f[0].isdigit():
            rows[section].append((float(f[0]), float(f[2]), float(f[3])))
    ideal = {a: s for a, s, _ in rows["no"]}  # singles before the front end
    return {m: [(a, ideal[a], lost) for a, _, lost in rows[m]] for m in ("non-paralyzable", "paralyzable")}


def main(dst):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.8))
    x = [i / 100 for i in range(301)]
    ax1.plot(x, x, ":", color=d2d.MUTED, linewidth=0.8, label="no dead time")
    ax1.plot(x, [v / (1 + v) for v in x], color=NP, linewidth=1.1, label="non-paralyzable")
    ax1.plot(x, [v * math.exp(-v) for v in x], color=P, linewidth=1.1, label="paralyzable")
    ax1.plot([1], [1 / math.e], "o", color=P, markersize=3)
    ax1.annotate("1/e at nτ = 1", (1, 1 / math.e), xytext=(1.5, 0.12),
                 arrowprops={"arrowstyle": "-", "linewidth": 0.6})
    ax1.set_xlim(0, 3)
    ax1.set_ylim(0, 1.2)
    ax1.set_xlabel("true rate nτ")
    ax1.set_ylabel("recorded rate mτ")
    ax1.set_title("one unit, Poisson arrivals")
    ax1.legend(frameon=False, loc="upper left")
    lost = read_lost()
    for model, color, f in (("non-paralyzable", NP, lambda v: 1 - 1 / (1 + v)),
                            ("paralyzable", P, lambda v: 1 - math.exp(-v))):
        pts = lost[model]
        a = [p[0] for p in pts]
        ax2.plot(a, [p[2] for p in pts], "o", color=color, markersize=3, label=f"{model}, simulated")
        ax2.plot(a, [100 * f(p[1] / BLOCKS * TAU) for p in pts], "-", color=color, linewidth=0.9,
                 label=f"{model}, model")
    ax2.set_xscale("log")
    ax2.set_xticks([5, 10, 20, 50, 100, 200, 500, 1000])
    ax2.set_xticklabels(["5", "10", "20", "50", "100", "200", "500", "1000"])
    ax2.set_xlabel("activity (MBq)")
    ax2.set_ylabel("singles lost (%)")
    ax2.set_title("1 µs per block, 72 blocks")
    ax2.legend(frameon=False)
    for ax in (ax1, ax2):
        ax.tick_params(labelsize=7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
