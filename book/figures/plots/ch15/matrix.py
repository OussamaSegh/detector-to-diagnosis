# SPDX-License-Identifier: MIT
"""Figure for Chapter 15: MiniDAQ's hazards on the risk matrix before and after their controls,
from docs/regulatory/risk/hazards.json and the plan's criterion (severity + probability <= 5).

    python3 book/tools/figures.py build book/figures/plots/ch15/matrix.py screen 3 pdf docs/regulatory/risk/hazards.json
"""
import collections
import json
import pathlib
import sys

from matplotlib.patches import FancyArrowPatch, Rectangle

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/regulatory/risk/hazards.json"


def main(dst):
    hz = json.loads(SRC.read_text())["hazards"]
    idx = lambda s: int(s[1:])  # noqa: E731
    before = collections.Counter((idx(h["probability_before"]), idx(h["severity"])) for h in hz)
    after = collections.Counter((idx(h["probability_after"]), idx(h["severity"])) for h in hz)
    moves = collections.Counter(((idx(h["probability_before"]), idx(h["severity"])), (idx(h["probability_after"]), idx(h["severity"]))) for h in hz)
    fig, ax = d2d.figure(height=2.5, width=0.62)
    for p in range(1, 6):
        for s in range(1, 5):
            ok = p + s <= 5
            ax.add_patch(Rectangle((p - 0.5, s - 0.5), 1, 1, facecolor=d2d.tint(d2d.CAT[2] if ok else d2d.SEM["mistakes"], 0.14),
                                   edgecolor="white", linewidth=1.5))
    for (a, b), n in moves.items():
        off = 0.12 * (b[1] - 2.5)
        ax.add_patch(FancyArrowPatch((a[0] - 0.22, a[1] + off), (b[0] + 0.22, b[1] + off), arrowstyle="-|>", mutation_scale=8,
                                     color=d2d.MUTED, linewidth=0.5 + 0.25 * n, connectionstyle="arc3,rad=-0.25"))
    for (p, s), n in before.items():
        ax.scatter(p, s, s=60 + 28 * n, facecolor="white", edgecolor=d2d.SEM["mistakes"], linewidth=1.2, zorder=3)
        ax.text(p, s, str(n), ha="center", va="center", fontsize=d2d.FONT_PT - 0.6, zorder=4)
    for (p, s), n in after.items():
        ax.scatter(p, s, s=60 + 28 * n, facecolor=d2d.PART, edgecolor=d2d.PART, zorder=3)
        ax.text(p, s, str(n), ha="center", va="center", fontsize=d2d.FONT_PT - 0.6, color="white", fontweight="bold", zorder=4)
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels(["P1\nimprobable", "P2\nremote", "P3\noccasional", "P4\nprobable", "P5\nfrequent"], fontsize=d2d.FONT_PT - 1)
    ax.set_yticks(range(1, 5))
    ax.set_yticklabels(["S1 negligible", "S2 minor", "S3 serious", "S4 critical"], fontsize=d2d.FONT_PT - 1)
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 4.5)
    ax.grid(False)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.scatter([], [], s=70, facecolor="white", edgecolor=d2d.SEM["mistakes"], label="before controls")
    ax.scatter([], [], s=70, facecolor=d2d.PART, label="after controls")
    ax.legend(loc="upper right", fontsize=d2d.FONT_PT - 1, frameon=True, framealpha=0.9, edgecolor="none")
    ax.text(5.42, 0.6, "not acceptable: S + P > 5", ha="right", va="bottom", fontsize=d2d.FONT_PT - 1.2)
    ax.text(0.58, 0.6, "acceptable", ha="left", va="bottom", fontsize=d2d.FONT_PT - 1.2)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
