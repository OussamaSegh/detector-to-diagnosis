# SPDX-License-Identifier: MIT
"""Figure for Chapter 16: the design and development file as an index, clause by clause, with the
number of evidence paths each clause names, from docs/regulatory/qms/design-file.json.

    python3 book/tools/figures.py build book/figures/plots/ch16/designfile.py screen 3 pdf docs/regulatory/qms/design-file.json
"""
import json
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/regulatory/qms/design-file.json"


def main(dst):
    clauses = json.loads(SRC.read_text())["clauses"]
    n = len(clauses)
    fig, ax = d2d.figure(height=0.15 * n + 0.7, width=0.85)
    for k, c in enumerate(clauses):
        y = n - 1 - k
        e = len(c["evidence"])
        design = c["clause"].startswith("7.3")
        col = d2d.PART if design else d2d.tint(d2d.PART, 0.45)
        if e:
            ax.barh(y, e, color=col, height=0.7)
            ax.text(e + 0.12, y, str(e), va="center", fontsize=d2d.FONT_PT - 1.2)
        else:
            ax.text(0.1, y, "none yet: a plan, not evidence", va="center", fontsize=d2d.FONT_PT - 1.2,
                    color=d2d.SEM["mistakes"], fontweight="bold")
    ax.set_yticks(range(n))
    ax.set_yticklabels([f"{c['clause']}  " + (c["topic"] if len(c["topic"]) <= 40 else c["topic"][:38].rstrip() + "…")
                        for c in reversed(clauses)], fontsize=d2d.FONT_PT - 1.4)
    ax.set_xlabel("evidence paths in the repository (design and development, 7.3, in full color)")
    ax.set_xlim(0, 9.5)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
