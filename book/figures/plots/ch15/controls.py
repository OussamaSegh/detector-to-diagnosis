# SPDX-License-Identifier: MIT
"""Figure for Chapter 15: risk controls per hazard by kind, in the standard's order of preference,
from docs/regulatory/risk/hazards.json.

    python3 book/tools/figures.py build book/figures/plots/ch15/controls.py screen 3 pdf docs/regulatory/risk/hazards.json
"""
import json
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/regulatory/risk/hazards.json"
KINDS = [("inherent", "inherent safety by design", d2d.PART, None), ("protective", "protective measure", d2d.CAT[0], "///"),
         ("information", "information for safety", d2d.CAT[1], "...")]


def main(dst):
    hz = json.loads(SRC.read_text())["hazards"]
    fig, ax = d2d.figure(height=2.3, width=0.9)
    for x, h in enumerate(hz):
        bottom = 0
        for kind, label, c, hatch in KINDS:
            n = sum(1 for c_ in h["controls"] if c_["type"] == kind)
            if n:
                ax.bar(x, n, bottom=bottom, color=c, hatch=hatch, edgecolor="white", linewidth=0.4, width=0.7,
                       label=label if x == 0 or label not in ax.get_legend_handles_labels()[1] else None)
                bottom += n
    ax.set_xticks(range(len(hz)))
    ax.set_xticklabels([h["id"] for h in hz], rotation=90, fontsize=d2d.FONT_PT - 1)
    ax.set_ylabel("risk controls")
    ax.grid(axis="x", visible=False)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(k[1]) for k in KINDS if k[1] in labels]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="upper right", fontsize=d2d.FONT_PT - 0.8, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
