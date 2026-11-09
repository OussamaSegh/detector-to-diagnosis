# SPDX-License-Identifier: MIT
"""Figure for Chapter 30: six realizations of the phantom, one protocol (OSEM 4 x 8, 4 mm filter):
each rod's contrast recovery, the mean and one SD (section 4), and how far each way of drawing the
region moves the number for realization 1 (section 5). From measurements/ch30/quality.txt.

    python3 book/tools/figures.py build book/figures/plots/ch30/repeat.py screen 6 pdf measurements/ch30/quality.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch30/quality.txt"


def table(text):
    rows = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")]
    return [[c.strip() for c in r.split("|")[1:-1]] for r in rows[1:]]


def main(dst):
    text = SRC.read_text()
    rep = table(text.split("## 4.")[1].split("## 5.")[0])
    roi = table(text.split("## 5.")[1])
    fig, (ax, bx) = d2d.figure(height=2.1, width=1.0, ncols=2, gridspec_kw={"width_ratios": [1, 1.5]})
    rods = ["12 mm", "8 mm", "5 mm"]
    real = [r for r in rep if r[0].isdigit()]
    mean = next(r for r in rep if r[0] == "mean")
    sd = next(r for r in rep if r[0] == "SD")
    for k in range(3):
        c = [d2d.PART, d2d.CAT[0], d2d.CAT[2]][k]
        ys = [float(r[1 + k]) for r in real]
        ax.scatter([k + (i - 2.5) * 0.06 for i in range(len(ys))], ys, color=c, s=10, zorder=3)
        m, s = float(mean[1 + k]), float(sd[1 + k])
        ax.errorbar([k + 0.35], [m], yerr=[s], color=d2d.INK, capsize=2.5, marker="_", ms=8, lw=0.9)
        ax.text(k + 0.45, m, f"{m:.2f}\n$\\pm${s:.3f}", fontsize=d2d.FONT_PT - 1.4, va="center", color=d2d.INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels(rods)
    ax.set_xlim(-0.5, 2.95)
    ax.set_ylabel("contrast recovery")
    ax.set_ylim(0.3, 1.85)
    ax.set_title("six realizations", fontsize=d2d.FONT_PT, color=d2d.INK)
    ax.grid(axis="x", visible=False)
    w = 0.15
    for j, r in enumerate(roi):
        c = [d2d.PART, d2d.CAT[0], d2d.CAT[1], d2d.CAT[3], d2d.MUTED][j]
        bx.bar([k + (j - 2) * w for k in range(3)], [float(v) for v in r[1:4]], width=w, color=c, label=r[0])
    bx.axhline(1, color=d2d.INK, lw=0.5)
    bx.set_xticks(range(3))
    bx.set_xticklabels(rods)
    bx.set_ylim(0.3, 1.85)
    bx.set_title("one image, five ways to draw the region", fontsize=d2d.FONT_PT, color=d2d.INK)
    bx.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.4, frameon=False, ncol=2)
    bx.grid(axis="x", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
