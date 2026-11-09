# SPDX-License-Identifier: MIT
"""Figure for Chapter 22: the front-end board's register map drawn from its specification,
hw/feb.toml: one row per register, 32 bits wide, fields colored, access kind on the right.

    python3 book/tools/figures.py build book/figures/plots/ch22/regmap.py screen 5 pdf hw/feb.toml
"""
import pathlib
import sys
import tomllib

from matplotlib.patches import Rectangle

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "hw/feb.toml"
ACCESS = {"ro": d2d.CAT[0], "rw": d2d.PART, "wo": d2d.CAT[1], "rw1c": d2d.CAT[3]}


def main(dst):
    regs = tomllib.loads(SRC.read_text())["register"]
    n = len(regs)
    fig, ax = d2d.figure(height=0.2 * n + 0.65, width=1.0)
    for k, r in enumerate(regs):
        y = n - 1 - k
        ax.add_patch(Rectangle((0, y + 0.1), 32, 0.8, facecolor="white", edgecolor=d2d.tint(d2d.MUTED, 0.5), linewidth=0.5))
        c = ACCESS[r["access"]]
        for j, f in enumerate(r.get("fields", [])):
            x = 31 - (f["lsb"] + f["width"] - 1)
            ax.add_patch(Rectangle((x, y + 0.1), f["width"], 0.8, facecolor=d2d.tint(c, 0.28 if j % 2 else 0.5),
                                   edgecolor="white", linewidth=0.8))
            if f["width"] >= 5:
                ax.text(x + f["width"] / 2, y + 0.5, f["name"], ha="center", va="center", fontsize=d2d.FONT_PT - 2.2)
            else:
                ax.text(x + f["width"] / 2, y + 0.5, f["name"][:1], ha="center", va="center", fontsize=d2d.FONT_PT - 2.4)
        ax.text(-0.4, y + 0.5, f"0x{r['address']:03X}  {r['name']}", ha="right", va="center", fontsize=d2d.FONT_PT - 1.4, family="monospace")
        ax.text(32.4, y + 0.5, r["access"], ha="left", va="center", fontsize=d2d.FONT_PT - 1.4, color=c, fontweight="bold")
    for b in (31, 24, 16, 8, 0):
        ax.text(31 - b + 0.5, n + 0.05, str(b), ha="center", va="bottom", fontsize=d2d.FONT_PT - 1.6, color=d2d.MUTED)
    ax.set_xlim(-12, 35)
    ax.set_ylim(-0.1, n + 0.5)
    ax.axis("off")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
