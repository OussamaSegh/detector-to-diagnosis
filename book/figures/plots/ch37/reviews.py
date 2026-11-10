# SPDX-License-Identifier: MIT
"""Figure for Chapter 37: the five independent reviews of a Part, the files each merge changed in
the book and elsewhere, from section 4 of measurements/ch37/provenance.txt.

    python3 book/tools/figures.py build book/figures/plots/ch37/reviews.py screen 9 pdf measurements/ch37/provenance.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch37/provenance.txt"
ROW = re.compile(r"^\s+(\w+): .*?(\d+) of them in the book, (\d+) elsewhere")
PARTS = ["IV", "V", "VI", "VII", "VIII"]  # one review per Part from Part IV on, in history order


def main(dst):
    rows = [m.groups() for m in map(ROW.match, SRC.read_text().split("4. Independent reviews")[1].splitlines()) if m]
    fig, ax = d2d.figure(height=1.7, width=0.8)
    for k, (c, book, other) in enumerate(rows):
        book, other = int(book), int(other)
        ax.bar(k, book, color=d2d.CAT[1], width=0.6, label="the book" if k == 0 else None)
        ax.bar(k, other, bottom=book, color=d2d.PART, width=0.6, label="code and records" if k == 0 else None)
        ax.text(k, book + other + 0.25, str(book + other), ha="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"Part {p}" for p in PARTS[:len(rows)]])
    ax.set_ylabel("files changed by the merge")
    ax.set_ylim(0, 13.5)
    ax.annotate("2 problem reports\n(MDQ-PR-059, -060)", (len(rows) - 1 + 0.3, 9.0), xytext=(-80, 20), textcoords="offset points",
                fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, ha="center",
                arrowprops=dict(arrowstyle="->", color=d2d.MUTED, lw=0.6))
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
