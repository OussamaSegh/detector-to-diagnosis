# SPDX-License-Identifier: MIT
"""Figure for Chapter 30: the hot-rod phantom with its regions of interest: each rod, and the
twelve background regions placed 8 mm or more from a rod's edge and inside 70 mm of the axis,
drawn at each size. Rods from measurements/ch28/reconstruct.py, the regions' centres from section 3
of measurements/ch30/quality.txt.

    python3 book/tools/figures.py build book/figures/plots/ch30/rois.py screen 6 pdf "measurements/ch30/quality.txt measurements/ch28/reconstruct.py"
"""
import pathlib
import re
import sys

import matplotlib.patches as mp

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]


def main(dst):
    rods = eval(re.search(r"^RODS = (\[.*?\])", (ROOT / "measurements/ch28/reconstruct.py").read_text(), re.M).group(1))
    text = (ROOT / "measurements/ch30/quality.txt").read_text().split("## 3.")[1]
    centres = [tuple(map(float, m)) for m in re.findall(r"\((-?\d+), (-?\d+)\)", text.split("Each rod's region")[0])]
    fig, ax = d2d.figure(height=2.6, width=0.5)
    ax.add_patch(mp.Circle((0, 0), 90, color=d2d.tint(d2d.CAT[0], 0.12), lw=0))
    ax.add_patch(mp.Circle((0, 0), 80, color=d2d.tint(d2d.PART, 0.18), lw=0))
    ax.add_patch(mp.Circle((0, 0), 70, fill=False, ls=":", color=d2d.MUTED, lw=0.7))
    for r, x, y in rods:
        ax.add_patch(mp.Circle((x, y), r, color=d2d.PART, lw=0))
        ax.text(x, y, f"{r:.0f}", ha="center", va="center", fontsize=d2d.FONT_PT - 1.5, color="white", fontweight="bold")
    for cx, cy in centres:
        for r, ls in ((12, "-"), (8, "--"), (5, ":")):
            ax.add_patch(mp.Circle((cx, cy), r, fill=False, ls=ls, lw=0.7, color=d2d.INK))
    ax.text(0, -86, "water 90 mm, activity 80 mm", ha="center", fontsize=d2d.FONT_PT - 1.5, color=d2d.CAT[0])
    ax.set_xlim(-95, 95)
    ax.set_ylim(-95, 95)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout(pad=0.1)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
