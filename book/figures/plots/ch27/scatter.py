# SPDX-License-Identifier: MIT
"""Figure for Chapter 27: four scatter estimates by tail fitting, each over the simulator's truth at
five positions s and under the object, from section 3 of measurements/ch27/corrections.txt.

    python3 book/tools/figures.py build book/figures/plots/ch27/scatter.py screen 6 pdf measurements/ch27/corrections.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch27/corrections.txt"
SHORT = ["Gaussian, a scale per slice", "model, a scale per slice", "model, one scale",
         "model, one scale, true randoms"]


def main(dst):
    text = SRC.read_text().split("## 3.")[1].split("## 4.")[0]
    lines = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("| Shape") and not l.startswith("|---")]
    head = next(l for l in text.splitlines() if l.startswith("| Shape"))
    s = [int(h.split("=")[1]) for h in head.split("|")[3:-1]]
    fig, ax = d2d.figure(height=2.5, width=0.85)
    for k, line in enumerate(lines):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        vals = [float(v) for v in cells[2:]]
        c = d2d.MUTED if k == 0 else [d2d.CAT[0], d2d.CAT[2], d2d.PART][k - 1]
        ax.plot(s, vals, color=c, marker=d2d.MARKERS[k], ms=4, lw=d2d.LINE_PT * (1.5 if k == 3 else 1),
                ls=d2d.DASHES[k], label=f"{SHORT[k]}: {float(cells[1]):.2f} under the object")
    ax.axhline(1, color=d2d.INK, lw=0.7)
    ax.set_yscale("log")
    ax.set_yticks([0.7, 1, 1.5, 2, 3, 4])
    ax.set_yticklabels(["0.7", "1", "1.5", "2", "3", "4"])
    ax.minorticks_off()
    ax.set_xlabel("s, mm from the centre")
    ax.set_ylabel("estimate / true scatter")
    ax.axvspan(92, 100, color=d2d.tint(d2d.PART, 0.15), lw=0)
    ax.text(96, 3.6, "tails", ha="center", fontsize=d2d.FONT_PT - 1, color=d2d.PART)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=d2d.FONT_PT - 1.3, frameon=False)
    ax.set_xlim(-3, 100)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
