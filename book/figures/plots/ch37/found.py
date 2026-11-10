# SPDX-License-Identifier: MIT
"""Figure for Chapter 37: what found the defects of a project written with an assistant, the 60
problem reports by the field "found", and the root causes where recorded, from section 3 of
measurements/ch37/provenance.txt.

    python3 book/tools/figures.py build book/figures/plots/ch37/found.py screen 9 pdf measurements/ch37/provenance.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch37/provenance.txt"
ROW = re.compile(r"^\s+(.+): (\d+)$")
SHORT = {"independent review of a Part": "independent review", "release checks and their reviews": "release checks",
         "the author's own tests and runs": "the author's tests", "design, development and measurement": "design and measurement"}


def main(dst):
    sec = SRC.read_text().split("3. Problem reports")[1].split("4.")[0]
    found = [(SHORT.get(m.group(1), m.group(1)), int(m.group(2))) for m in map(ROW.match, sec.splitlines()) if m]
    found.sort(key=lambda r: r[1])
    causes = dict(p.rsplit(" ", 1) for p in re.search(r"root cause categories: (.*)", sec).group(1).split(", "))
    causes = sorted(((k, int(v)) for k, v in causes.items()), key=lambda r: (r[0] == "none recorded", -r[1]))
    fig, (ax, bx) = d2d.figure(height=2.0, width=1.0, ncols=2, gridspec_kw={"width_ratios": [1.3, 1]})
    run = {"release checks", "CI runs", "the author's tests", "fuzzing"}
    for k, (n, v) in enumerate(found):
        c = d2d.PART if n in run else d2d.CAT[0]
        ax.barh(k, v, color=c, height=0.66)
        ax.text(v + 0.4, k, str(v), va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    ax.set_yticks(range(len(found)))
    ax.set_yticklabels([n for n, _ in found])
    ax.set_xlabel("problem reports")
    ax.set_title("found by", fontsize=d2d.FONT_PT, color=d2d.INK)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(v for _, v in found) * 1.18)
    for k, (n, v) in enumerate(reversed(causes)):
        c = d2d.tint(d2d.MUTED, 0.45) if n == "none recorded" else d2d.CAT[1]
        bx.barh(k, v, color=c, height=0.66)
        bx.text(v + 0.4, k, str(v), va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    bx.set_yticks(range(len(causes)))
    bx.set_yticklabels([n for n, _ in reversed(causes)])
    bx.set_xlim(0, max(v for _, v in causes) * 1.22)
    bx.set_xlabel("problem reports")
    bx.set_title("root cause", fontsize=d2d.FONT_PT, color=d2d.INK)
    bx.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
