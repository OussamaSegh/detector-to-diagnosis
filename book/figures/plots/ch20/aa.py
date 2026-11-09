# SPDX-License-Identifier: MIT
"""Figure for Chapter 20: fifteen A/A comparisons of a build with itself on the reference machine,
every benchmark of every job, against the gate's two conditions (from measurements/ch20/aa-local.txt).

    python3 book/tools/figures.py build book/figures/plots/ch20/aa.py screen 4 pdf measurements/ch20/aa-local.txt
"""
import math
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch20/aa-local.txt"
LINE = re.compile(r"^(BM_\S+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)")
NAMES = {"BM_DecodePacked": "decode", "BM_EnergyFilter/1": "filter, branchless", "BM_EnergyFilter/3": "filter, AVX-512",
         "BM_HistogramRecord": "histogram", "BM_Pipeline": "pipeline", "BM_SortFunctor": "sort"}


def short(name):
    return next(v for k, v in NAMES.items() if name.startswith(k))


def main(dst):
    pts = []
    for line in SRC.read_text().splitlines():
        m = LINE.match(line)
        if m:
            pts.append((short(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4)))
    names = list(dict.fromkeys(p[0] for p in pts))
    fig, ax = d2d.figure(height=2.5, width=0.75)
    ax.axvspan(0.80, 0.95, ymin=0, ymax=1, color=d2d.tint(d2d.SEM["mistakes"], 0.08), linewidth=0)
    ax.axvline(0.95, color=d2d.SEM["mistakes"], linestyle="--", linewidth=0.9)
    ax.axhline(2, color=d2d.SEM["mistakes"], linestyle=":", linewidth=0.9)
    for k, n in enumerate(names):
        xs = [p[1] for p in pts if p[0] == n]
        ys = [-math.log10(max(p[2], 1e-6)) for p in pts if p[0] == n]
        ax.scatter(xs, ys, s=16, marker=d2d.MARKERS[k], color=d2d.CAT[k] if k else d2d.PART, label=n, alpha=0.9, linewidths=0)
    for name, x, p, verdict in pts:
        if verdict == "REGRESSION":
            ax.annotate("the one false alarm\n0.946, p = 0.0045", xy=(x, -math.log10(p)), xytext=(0.855, 2.75), fontsize=d2d.FONT_PT - 1,
                        arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.6})
    ax.text(0.952, 3.55, "alarm only if slower than 0.95\nand p < 0.01 (both)", fontsize=d2d.FONT_PT - 1.1, va="top")
    ax.set_xlim(0.84, 1.08)
    ax.set_ylim(0, 3.6)
    ax.set_xlabel("median speed, build against itself (1 = equal)")
    ax.set_ylabel("−log₁₀ p (one-sided)".replace("₁₀", "10"))
    ax.legend(loc="lower left", bbox_to_anchor=(0.13, 0.0), fontsize=d2d.FONT_PT - 1.1, frameon=False, ncol=1)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
