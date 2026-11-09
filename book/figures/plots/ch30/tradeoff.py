# SPDX-License-Identifier: MIT
"""Figure for Chapter 30: contrast recovery against background variability for each rod, OSEM at
2, 4, 8 and 16 iterations, without a filter and with Gaussian filters of 4 and 6 mm FWHM, from
section 3 of measurements/ch30/quality.txt.

    python3 book/tools/figures.py build book/figures/plots/ch30/tradeoff.py screen 6 pdf measurements/ch30/quality.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch30/quality.txt"


def main(dst):
    text = SRC.read_text().split("## 3.")[1].split("## 4.")[0]
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")][1:]
    fig, axes = d2d.figure(height=2.0, width=1.0, ncols=3, sharey=True)
    for k, (ax, rod) in enumerate(zip(axes, ("12 mm", "8 mm", "5 mm"))):
        for j, (filt, mk) in enumerate(((None, "o"), ("4 mm filter", "s"), ("6 mm filter", "^"))):
            sel = [r for r in rows if (filt in r[0] if filt else "filter" not in r[0])]
            xs = [float(r[4 + k].rstrip("%")) for r in sel]
            ys = [float(r[1 + k]) for r in sel]
            c = [d2d.PART, d2d.CAT[0], d2d.CAT[2]][j]
            ax.plot(xs, ys, color=c, marker=mk, ms=3.5, lw=d2d.LINE_PT, ls=d2d.DASHES[j], label=filt or "no filter")
            if j == 0:
                for r, x, y in zip(sel, xs, ys):
                    ax.annotate(r[0].split()[1], (x, y), xytext=(3, 3), textcoords="offset points", fontsize=d2d.FONT_PT - 1.6, color=c)
        ax.axhline(1, color=d2d.INK, lw=0.5)
        ax.set_title(f"{rod} rod", fontsize=d2d.FONT_PT, color=d2d.INK)
        ax.set_xlabel("background variability, %")
    axes[0].set_ylabel("contrast recovery")
    axes[0].set_ylim(0.25, 1.2)
    axes[2].legend(loc="lower right", fontsize=d2d.FONT_PT - 1.3, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
