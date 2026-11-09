# SPDX-License-Identifier: MIT
"""Figure for Chapter 7: the 175 findings of the first static analysis run, by check and by what
was done with them (the chapter's triage table).

    python3 book/tools/figures.py build book/figures/plots/ch07/triage.py screen 1 pdf
"""
import sys

import d2d

# check, fixed, suppressed, disabled (the "mixed" cert-err33-c row counted as fixed or checked)
ROWS = [("pro-type-vararg", 0, 0, 32), ("pro-type-union-access", 0, 26, 0), ("cert-err33-c", 25, 0, 0),
        ("pro-bounds-array-to-pointer-decay", 0, 0, 13), ("special-member-functions", 11, 0, 0),
        ("cert-err34-c (atoi)", 11, 0, 0), ("assignment-in-if-condition", 9, 0, 0),
        ("unnecessary-value-param", 7, 0, 0), ("pro-type-reinterpret-cast", 0, 7, 0),
        ("redundant-member-init", 0, 0, 6), ("concurrency-mt-unsafe", 6, 0, 0), ("12 other checks", 17, 5, 0)]
KINDS = [("fixed in the code", d2d.CAT[2], None), ("suppressed with a reason", d2d.CAT[1], "///"),
         ("check disabled with a reason", d2d.MUTED, "...")]


def main(dst):
    fig, ax = d2d.figure(height=2.9, width=0.85)
    n = len(ROWS)
    for k, row in enumerate(ROWS):
        y = n - 1 - k
        left = 0
        for j, (label, c, h) in enumerate(KINDS):
            v = row[1 + j]
            if v:
                ax.barh(y, v, left=left, color=c, hatch=h, edgecolor="white", linewidth=0.4, height=0.68,
                        label=label if label not in ax.get_legend_handles_labels()[1] else None)
                left += v
        ax.text(left + 0.6, y, str(left), va="center", fontsize=d2d.FONT_PT - 0.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in reversed(ROWS)], family="monospace", fontsize=d2d.FONT_PT - 0.9)
    ax.set_xlim(0, 36)
    ax.set_xlabel("findings in the first run (175 in all; zero after the third)")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="center right", fontsize=d2d.FONT_PT - 0.7, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
