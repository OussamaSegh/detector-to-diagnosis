# SPDX-License-Identifier: MIT
"""Figure for Chapter 34: files that change together. The twenty most coupled pairs in minidaq/,
from measurements/ch34/coupling.txt (Exercise 34.1's solution over the git history): shared commits
as the cell's number, coupling as its color.

    python3 book/tools/figures.py build book/figures/plots/ch34/coupling.py screen 8 pdf measurements/ch34/coupling.txt
"""
import pathlib
import sys

import matplotlib.colors as mc
import numpy as np

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch34/coupling.txt"


def short(path):
    p = path.replace("minidaq/", "", 1)
    for a, b in (("include/minidaq/", "inc/"), ("tests/unit/", "test/"), ("src/", "")):
        p = p.replace(a, b)
    return p


def main(dst):
    pairs = []
    for line in SRC.read_text().splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0].startswith("minidaq/"):
            pairs.append((short(parts[0]), short(parts[1]), int(parts[2]), float(parts[3])))
    files = []
    for a, b, *_ in pairs:
        for f in (a, b):
            if f not in files:
                files.append(f)
    n = len(files)
    m = np.full((n, n), np.nan)
    shared = {}
    for a, b, s, c in pairs:
        i, j = files.index(a), files.index(b)
        m[i, j] = m[j, i] = c
        shared[(i, j)] = shared[(j, i)] = s
    cmap = mc.LinearSegmentedColormap.from_list("d2d", [d2d.tint(d2d.PART, 0.15), d2d.PART])
    fig, ax = d2d.figure(height=3.4, width=1.0)
    ax.imshow(np.ma.masked_invalid(m), cmap=cmap, vmin=0.4, vmax=1.0)
    for (i, j), s in shared.items():
        ax.text(j, i, str(s), ha="center", va="center", fontsize=d2d.FONT_PT - 2, color="white" if m[i, j] > 0.7 else d2d.INK)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(files, rotation=60, ha="right", fontsize=d2d.FONT_PT - 1.8)
    ax.set_yticklabels(files, fontsize=d2d.FONT_PT - 1.8)
    ax.grid(False)
    ax.set_xticks(np.arange(n + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(n + 1) - 0.5, minor=True)
    ax.grid(which="minor", color=d2d.tint(d2d.MUTED, 0.25), lw=0.4)
    ax.tick_params(which="minor", length=0)
    fig.tight_layout(pad=0.2)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
