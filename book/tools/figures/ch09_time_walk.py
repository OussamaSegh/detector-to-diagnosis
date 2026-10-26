# SPDX-License-Identifier: MIT
"""Figure for Chapter 9: leading-edge time walk and constant-fraction timing,
on the pulse model of Exercise 9.4.

    python3 book/tools/figures/ch09_time_walk.py book/src/img/ch09-time-walk.png
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../exercises/ch09/e4_time_walk/solution"))
import time_walk as tw  # noqa: E402

THRESHOLD = 0.1  # exaggerated for the figure (the exercise uses 0.02)
ENERGIES = [(150, "#e08a2b"), (300, "#7a9a3a"), (511, "#1f5fa8")]


def main(dst):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.9), dpi=300, sharey=True)
    ts = [i * 0.005 for i in range(0, 1001)]
    for ax, title in ((ax1, "fixed threshold: walk"), (ax2, "constant fraction (20%): no walk")):
        for kev, color in ENERGIES:
            a = kev / 511.0
            ax.plot(ts, [tw.pulse(t, a) for t in ts], color=color, linewidth=1.2, label=f"{kev} keV")
            if ax is ax1:
                t = tw.leading_edge_ns(THRESHOLD, a)
                y = THRESHOLD
            else:
                t = tw.constant_fraction_ns(0.2, a)
                y = tw.pulse(t, a)
            ax.plot([t], [y], "o", color=color, markersize=4)
            ax.axvline(t, color=color, linewidth=0.6, linestyle=":")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("time (ns)")
        ax.set_xlim(0, 3)
    ax1.axhline(THRESHOLD, color="black", linewidth=0.8, linestyle="--")
    ax1.text(1.9, THRESHOLD + 0.03, "threshold", fontsize=8)
    ax1.set_ylabel("amplitude (511 keV = 1)")
    ax1.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1])
