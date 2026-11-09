# SPDX-License-Identifier: MIT
"""Figure for Chapter 31: five ways to read a 1 GiB list-mode file, their median time against their
peak anonymous memory, from section 1 of measurements/ch31/analysis.txt.

    python3 book/tools/figures.py build book/figures/plots/ch31/readers.py screen 7 pdf measurements/ch31/analysis.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch31/analysis.txt"
SHORT = ["the whole file in memory", "mapped, decoded whole", "chunks of 2^20, with pair counts",
         "chunks of 2^20, without pair counts", "mapped, CRCs only"]


def main(dst):
    text = SRC.read_text().split("## 1.")[1].split("## 2.")[0]
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")][1:]
    fig, ax = d2d.figure(height=2.0, width=0.75)
    for k, r in enumerate(rows):
        t = float(r[1].split(",")[1])
        mem = float(r[2].replace(",", ""))
        c = [d2d.MUTED, d2d.CAT[0], d2d.CAT[3], d2d.PART, d2d.CAT[2]][k]
        ax.scatter(mem, t, color=c, s=24, marker=d2d.MARKERS[k], zorder=3)
        ax.annotate(SHORT[k], (mem, t), xytext=(6, -3 if k != 1 else 4), textcoords="offset points",
                    fontsize=d2d.FONT_PT - 1.2, color=c)
    ax.set_xscale("log")
    ax.set_xlim(8, 40000)
    ax.set_ylim(0, 16)
    ax.set_xlabel("peak anonymous memory, MiB (the file is 1,024 MiB)")
    ax.set_ylabel("median time, s")
    ax.axvline(1024, color=d2d.MUTED, lw=0.6, ls=":")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
