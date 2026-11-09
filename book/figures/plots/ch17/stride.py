# SPDX-License-Identifier: MIT
"""Figure for Chapter 17: STRIDE per element. One square per threat in the cell of its element and
category, colored by status; hatched cells are categories that do not apply to the element's kind.
From docs/regulatory/security/threats.json.

    python3 book/tools/figures.py build book/figures/plots/ch17/stride.py screen 3 pdf docs/regulatory/security/threats.json
"""
import json
import pathlib
import sys

from matplotlib.patches import Patch, Rectangle

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/regulatory/security/threats.json"
STATUS = [("mitigated", d2d.CAT[2], None), ("environment", d2d.CAT[0], "////"), ("accepted", d2d.CAT[1], "...."),
          ("not_applicable", d2d.tint(d2d.MUTED, 0.45), None)]


def main(dst):
    d = json.loads(SRC.read_text())
    cats = list(d["stride"])
    els = d["elements"]
    fig, ax = d2d.figure(height=0.2 * len(els) + 0.9, width=0.72)
    for r, e in enumerate(els):
        y = len(els) - 1 - r
        for c, cat in enumerate(cats):
            if cat not in d["applies"][e["kind"]]:
                ax.add_patch(Rectangle((c, y), 1, 1, facecolor="white", edgecolor=d2d.tint(d2d.MUTED, 0.3), hatch="xxxx", linewidth=0))
                continue
            ax.add_patch(Rectangle((c, y), 1, 1, facecolor=d2d.tint(d2d.PART, 0.06), edgecolor="white", linewidth=1.2))
            ts = [t for t in d["threats"] if t["element"] == e["id"] and t["stride"] == cat]
            for k, t in enumerate(ts):
                col, hatch = next((s[1], s[2]) for s in STATUS if s[0] == t["status"])
                ax.add_patch(Rectangle((c + 0.1 + 0.27 * (k % 3), y + 0.55 - 0.42 * (k // 3)), 0.22, 0.34, facecolor=col,
                                       hatch=hatch, edgecolor="white", linewidth=0.3))
    ax.set_xticks([c + 0.5 for c in range(len(cats))])
    ax.set_xticklabels(cats, fontweight="bold")
    ax.xaxis.tick_top()
    ax.set_yticks([len(els) - 0.5 - r for r in range(len(els))])
    ax.set_yticklabels([f"{e['id']} ({e['kind']})" for e in els], fontsize=d2d.FONT_PT - 1.1)
    ax.set_xlim(0, len(cats))
    ax.set_ylim(0, len(els))
    ax.tick_params(length=0)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    n = {s[0]: sum(1 for t in d["threats"] if t["status"] == s[0]) for s in STATUS}
    ax.legend(handles=[Patch(facecolor=s[1], hatch=s[2], edgecolor="white", label=f"{s[0].replace('_', ' ')} ({n[s[0]]})") for s in STATUS],
              loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=d2d.FONT_PT - 1.0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
