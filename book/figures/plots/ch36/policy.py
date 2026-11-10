# SPDX-License-Identifier: MIT
"""Figure for Chapter 36: MiniDAQ's history against commit policy 1, the commits that break each
rule over the whole history and since the first change request, from section 2 of
measurements/ch36/history.txt.

    python3 book/tools/figures.py build book/figures/plots/ch36/policy.py screen 9 pdf measurements/ch36/history.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch36/history.txt"
ROW = re.compile(r"^\s+(whole history|since CR-0001)\s+\((\d+) commits\): (.*)$")


def main(dst):
    rows = []
    for m in map(ROW.match, SRC.read_text().split("2. The policy")[1].split("3.")[0].splitlines()):
        if m:
            counts = dict((k, int(v)) for k, v in (p.split() for p in m.group(3).split(", ")))
            rows.append((m.group(1), int(m.group(2)), counts))
    rules = list(rows[0][2])
    fig, ax = d2d.figure(height=1.9, width=0.85)
    w = 0.38
    for j, (name, total, counts) in enumerate(rows):
        c = d2d.MUTED if j == 0 else d2d.PART
        xs = [i + (j - 0.5) * w for i in range(len(rules))]
        vals = [counts[r] / total * 100 for r in rules]
        ax.bar(xs, vals, width=w, color=c, label=f"{name} ({total} commits)")
        for x, r in zip(xs, rules):
            ax.text(x, counts[r] / total * 100 + 1.5, str(counts[r]), ha="center", fontsize=d2d.FONT_PT - 1.6, color=d2d.INK)
    ax.set_xticks(range(len(rules)))
    ax.set_xticklabels(rules)
    ax.set_ylabel("commits breaking the rule, %")
    ax.set_ylim(0, 112)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
