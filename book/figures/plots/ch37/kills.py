# SPDX-License-Identifier: MIT
"""Figure for Chapter 37: which test of Exercise 37.3 catches which version of the coincidence
check, the starter's two tests and the solution's eight against the function and its seven
mutants, from measurements/ch37/mutants.txt.

    python3 book/tools/figures.py build book/figures/plots/ch37/kills.py screen 9 pdf measurements/ch37/mutants.txt
"""
import pathlib
import re
import sys

import d2d
from matplotlib.patches import Rectangle

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch37/mutants.txt"


def main(dst):
    text = SRC.read_text()
    names = [v.split(" ", 1)[1] for v in re.search(r"versions: (.*)", text).group(1).split("; ")]
    blocks = {}
    for which in ("starter", "solution"):
        sec = text.split(f"\n{which} (")[1].split("mutants caught")[0]
        blocks[which] = [(m.group(1), [int(x) for x in m.group(2).split()])
                         for m in re.finditer(r"^\s+(\w+)\s+([01 ]+)$", sec, re.M)]
    rows = [("the assistant's " + n, v, "starter") for n, v in blocks["starter"]]
    rows += [(n, v, "solution") for n, v in blocks["solution"][2:]]
    fig, ax = d2d.figure(height=2.5, width=1.0)
    for i, (n, v, which) in enumerate(rows):
        y = len(rows) - 1 - i + (0.4 if which == "starter" else 0)
        for j, f in enumerate(v):
            c = (d2d.PART if j else d2d.CAT[3]) if f else d2d.tint(d2d.MUTED, 0.18)
            ax.add_patch(Rectangle((j + 0.06, y + 0.06), 0.88, 0.88, color=c, lw=0))
        ax.text(-0.15, y + 0.5, re.sub(r"(?<!^)(?=[A-Z])", " ", n.replace("the assistant's ", "")).lower()
                + (" (the assistant's)" if which == "starter" else ""), ha="right", va="center", fontsize=d2d.FONT_PT - 1.0, color=d2d.INK)
    top = len(rows) + 0.4
    for j, m in enumerate(names):
        ax.text(j + 0.5, top + 0.15, f"{j} {m}", rotation=40, ha="left", va="bottom", fontsize=d2d.FONT_PT - 1.2,
                color=d2d.INK if j else d2d.CAT[2])
    ax.axhline(len(rows) - 2 + 0.2, color=d2d.INK, lw=0.6)
    ax.set_xlim(-0.05, len(names) + 0.05)
    ax.set_ylim(0, top + 2.6)
    ax.axis("off")
    ax.text(len(names) + 0.15, len(rows) - 2 + 1.4, "caught\nnone", va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    ax.text(len(names) + 0.15, (len(rows) - 2) / 2, "caught\nall 7", va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
