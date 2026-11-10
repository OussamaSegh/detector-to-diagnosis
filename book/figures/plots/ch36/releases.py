# SPDX-License-Identifier: MIT
"""Figure for Chapter 36: releases on the history, the dated versions of CHANGELOG.md on a time
line, each with the number of lines its entry holds.

    python3 book/tools/figures.py build book/figures/plots/ch36/releases.py screen 9 pdf CHANGELOG.md
"""
import datetime as dt
import pathlib
import re
import sys

import matplotlib.dates as mdates

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "CHANGELOG.md"
HEAD = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d\d-\d\d)")


def main(dst):
    lines = SRC.read_text().splitlines()
    marks = [(i, m.group(1), dt.date.fromisoformat(m.group(2))) for i, m in ((i, HEAD.match(l)) for i, l in enumerate(lines)) if m]
    ends = [i for i, *_ in marks[1:]] + [len(lines)]
    rel = [(v, d, sum(1 for l in lines[i + 1:e] if l.strip())) for (i, v, d), e in zip(marks, ends)]
    rel.sort(key=lambda r: (r[1], r[0]))
    fig, ax = d2d.figure(height=1.9, width=1.0)
    seen = {}
    for v, d, n in rel:
        k = seen.get(d, 0)
        seen[d] = k + 1
        c = d2d.PART if v.endswith(".0.0") else d2d.CAT[0]
        ax.vlines(d, 0, n, color=d2d.tint(c, 0.5), lw=1)
        ax.scatter(d, n, color=c, s=18, zorder=3)
        ax.annotate(v, (d, n), xytext=(3 if k == 0 else -3, 4), textcoords="offset points", fontsize=d2d.FONT_PT - 1.2,
                    color=c, ha="left" if k == 0 else "right")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_ylabel("lines in its CHANGELOG entry")
    ax.set_ylim(0, max(r[2] for r in rel) * 1.25)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
