# SPDX-License-Identifier: MIT
"""Chapter 9: leading-edge time walk and constant-fraction timing, on the pulse model of
Exercise 9.4 (exercises/ch09/e4_time_walk/solution/time_walk.py). Threshold exaggerated."""
import pathlib
import sys

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "exercises/ch09/e4_time_walk/solution"))
import time_walk as tw  # noqa: E402

THRESHOLD = 0.1  # exaggerated for the figure (the exercise uses 0.02)
ENERGIES = [150, 300, 511]
fig, (a1, a2) = d2d.figure(height=2.4, ncols=2, sharey=True)
ts = [i * 0.005 for i in range(0, 601)]
for ax, title in ((a1, "Fixed threshold: the time walks"), (a2, "Constant fraction (20%): no walk")):
    for i, kev in enumerate(ENERGIES):
        a = kev / 511.0
        c = d2d.CAT[i]
        ax.plot(ts, [tw.pulse(t, a) for t in ts], color=c, linestyle=d2d.DASHES[i], label=f"{kev} keV")
        if ax is a1:
            t, y = tw.leading_edge_ns(THRESHOLD, a), THRESHOLD
        else:
            t = tw.constant_fraction_ns(0.2, a)
            y = tw.pulse(t, a)
        ax.plot([t], [y], marker=d2d.MARKERS[i], color=c, markeredgecolor="white", markersize=6, zorder=5)
        ax.axvline(t, color=c, linewidth=0.7, linestyle=":")
    ax.set_title(title)
    ax.set_xlabel("time (ns)")
    ax.set_xlim(0, 3)
a1.axhline(THRESHOLD, color=d2d.PART, linewidth=1.0, linestyle="--")
a1.text(1.95, THRESHOLD + 0.03, "threshold", color=d2d.PART, fontweight="bold")
a1.set_ylabel("amplitude (511 keV = 1)")
a1.legend(loc="upper left")
fig.tight_layout(w_pad=2)
d2d.save(fig)
