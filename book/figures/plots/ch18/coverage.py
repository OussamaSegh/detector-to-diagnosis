# SPDX-License-Identifier: MIT
"""Figure for Chapter 18: line, branch and MC/DC coverage per software item, from
measurements/ch18/coverage/summary.json (unit tests only, Clang source-based coverage).

    python3 book/tools/figures.py build book/figures/plots/ch18/coverage.py screen 4 pdf measurements/ch18/coverage
"""
import json
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch18/coverage/summary.json"
KINDS = [("lines", "lines", d2d.PART, "o"), ("branches", "branches", d2d.CAT[2], "s"), ("mcdc", "MC/DC conditions", d2d.CAT[1], "^")]


def pct(v):
    return 100.0 * v[0] / v[1] if v and v[1] else None


def main(dst):
    d = json.loads(SRC.read_text())
    items = [k for k in d if isinstance(d[k], dict) and d[k].get("lines") and k not in ("all", "tools")]
    items.sort(key=lambda k: pct(d[k]["lines"]))
    fig, ax = d2d.figure(height=0.16 * len(items) + 0.75, width=0.8)
    for y, it in enumerate(items):
        vals = [pct(d[it].get(k)) for k, *_ in KINDS]
        present = [v for v in vals if v is not None]
        ax.plot([min(present), max(present)], [y, y], color=d2d.tint(d2d.MUTED, 0.5), linewidth=0.8, zorder=1)
        for (k, label, c, m), v in zip(KINDS, vals):
            if v is not None:
                ax.scatter(v, y, color=c, marker=m, s=22, zorder=3, label=label if y == 0 else None)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(items, fontsize=d2d.FONT_PT - 0.8, family="monospace")
    ax.set_xlim(-3, 103)
    ax.set_xlabel("covered by the unit tests (%)")
    ax.tick_params(axis="y", length=0)
    ax.annotate("the client: system tests\n(Chapter 19)", xy=(2.5, 0), xytext=(16, 1.3), fontsize=d2d.FONT_PT - 1,
                va="center", arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.6})
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 0.9, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
