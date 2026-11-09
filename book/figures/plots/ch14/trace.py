# SPDX-License-Identifier: MIT
"""Figure for Chapter 14: the trace matrix as a map. One square per requirement, grouped by area,
shaded by how many tests name it, from docs/regulatory/trace-matrix.md (the generated matrix).

    python3 book/tools/figures.py build book/figures/plots/ch14/trace.py screen 3 pdf docs/regulatory/trace-matrix.md
"""
import pathlib
import re
import sys

from matplotlib.patches import Patch, Rectangle

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/regulatory/trace-matrix.md"
ROW = re.compile(r"^\| (SRS-([A-Z]+)-\d+) \| [^|]* \| ([A-Z,/ ]+) \| ([^|]*) \|")


def rows():
    out = {}
    for line in SRC.read_text().splitlines():
        m = ROW.match(line)
        if m:
            method = m.group(3).strip()
            tests = m.group(4).count("<br>") + 1 if m.group(4).strip() and method == "T" else 0
            out.setdefault(m.group(2), []).append((tests, method))
    return out


def shade(n, method):
    if n == 0:
        return d2d.tint(d2d.MUTED, 0.35) if method != "T" else d2d.SEM["mistakes"]
    return d2d.tint(d2d.PART, {1: 0.3, 2: 0.55, 3: 0.55}.get(n, 0.8 if n < 8 else 1.0))


def main(dst):
    data = rows()
    areas = sorted(data, key=lambda a: -len(data[a]))
    per_row = 24
    lines = []
    for a in areas:
        reqs = data[a]
        for k in range(0, len(reqs), per_row):
            lines.append((a if k == 0 else "", reqs[k:k + per_row]))
    half = (len(lines) + 1) // 2
    fig, ax = d2d.figure(height=0.155 * half + 0.85, width=1.0)
    for i, (a, reqs) in enumerate(lines):
        x0, y = (0, i) if i < half else (per_row + 6, i - half)
        for x, (n, method) in enumerate(reqs):
            ax.add_patch(Rectangle((x0 + x, -y), 0.86, 0.86, color=shade(n, method), linewidth=0))
        ax.text(x0 - 0.5, -y + 0.43, a, ha="right", va="center", fontsize=d2d.FONT_PT - 1.2, family="monospace")
    ax.set_xlim(-3.2, 2 * per_row + 6)
    ax.set_ylim(-half + 0.8, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    total = sum(len(v) for v in data.values())
    tested = sum(1 for v in data.values() for n, _ in v if n)
    other = total - sum(1 for v in data.values() for _, m in v if m == "T")
    handles = [Patch(color=shade(1, "T"), label="1 test"), Patch(color=shade(2, "T"), label="2 to 3"),
               Patch(color=shade(5, "T"), label="4 to 7"), Patch(color=shade(9, "T"), label="8 or more"),
               Patch(color=shade(0, "M"), label="no test by design")]
    if any(n == 0 and m == "T" for v in data.values() for n, m in v):
        handles.append(Patch(color=d2d.SEM["mistakes"], label="gap"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 0.0), ncol=len(handles), frameon=False,
              fontsize=d2d.FONT_PT - 1.0, handlelength=1.0, columnspacing=1.0)
    ax.set_title(f"{total} requirements: {tested} named by at least one test, {other} verified by measurement, inspection or demonstration", fontsize=d2d.FONT_PT, loc="left")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
