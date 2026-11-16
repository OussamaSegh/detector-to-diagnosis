# SPDX-License-Identifier: MIT
"""Figure for Chapter 38: what the time base monitor estimated for a step of block 29's clock,
with its standard deviation, against the warning and alarm limits, and the largest offset any
block reached in the healthy runs, from measurements/ch38/time_base.txt.

    python3 book/tools/figures.py build book/figures/plots/ch38/steps.py screen 10 pdf measurements/ch38/time_base.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch38/time_base.txt"
STEP = re.compile(r"^\| step of (\d+) ps \| (\w+) \| (-?\d+) \+- (\d+) \|")
LARGEST = re.compile(r"the largest offset of any block (\d+) ps")
COLOR = {"normal": d2d.CAT[2], "warning": d2d.CAT[4], "alarm": d2d.SEM["mistakes"]}


def main(dst):
    text = SRC.read_text()
    rows = [m.groups() for m in map(STEP.match, text.splitlines()) if m]
    largest = int(LARGEST.search(text).group(1))
    fig, ax = d2d.figure(height=2.3, width=0.8)
    ax.axhspan(-largest, largest, color=d2d.tint(d2d.MUTED, 0.15), zorder=0, linewidth=0)
    ax.text(640, -largest + 10, f"healthy runs: every block within {largest} ps", fontsize=d2d.FONT_PT - 1.2,
            color=d2d.MUTED, va="bottom", ha="right")
    for y, name in ((100, "warning limit"), (250, "alarm limit")):
        ax.axhline(y, color=d2d.MUTED, linestyle=":", linewidth=0.9)
        ax.text(640, y, name, fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED, va="center", ha="right",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.plot([0, 650], [0, 650], color=d2d.RULE, linewidth=0.8, zorder=1)
    for step, level, off, sd in rows:
        step, off, sd = int(step), int(off), int(sd)
        ax.errorbar(step, off, yerr=5 * sd, color=COLOR[level], marker="o", markersize=4.5, capsize=2.5,
                    linewidth=1.1, zorder=3)
        ax.text(step + 12, off, level, fontsize=d2d.FONT_PT - 1.1, color=COLOR[level], va="center",
                rotation=0 if step > 250 else 90, ha="left" if step > 250 else "center")
    ax.set_xlim(0, 650)
    ax.set_ylim(-150, 680)
    ax.set_xlabel("step of block 29's clock (ps)")
    ax.set_ylabel("offset estimated (ps)")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
