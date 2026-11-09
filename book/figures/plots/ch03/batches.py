# SPDX-License-Identifier: MIT
"""Figure for Chapter 3: the five-stage pipeline against the batch size, and the sort stage alone,
from the chapter's tables (bm_pipeline, five repetitions; sort timed separately).

    python3 book/tools/figures.py build book/figures/plots/ch03/batches.py screen 1 pdf
"""
import sys

import d2d

PIPE = [(64, 40.1, 42.6, 43.6), (512, 45.5, 47.3, 48.3), (4096, 32.6, 33.1, 33.7)]
SORT = [(64, 90, 90), (512, 42, 50), (4096, 35, 37)]


def main(dst):
    fig, ax = d2d.figure(height=2.3, width=0.62)
    x = [p[0] for p in PIPE]
    ax.plot(x, [p[2] for p in PIPE], marker="o", color=d2d.PART, label="whole pipeline (median)")
    ax.fill_between(x, [p[1] for p in PIPE], [p[3] for p in PIPE], color=d2d.tint(d2d.PART, 0.25), linewidth=0)
    ax.plot(x, [(s[1] + s[2]) / 2 for s in SORT], marker="s", linestyle="--", color=d2d.CAT[3],
            label="sort stage alone")
    ax.errorbar(x, [(s[1] + s[2]) / 2 for s in SORT], yerr=[(s[2] - s[1]) / 2 for s in SORT],
                fmt="none", ecolor=d2d.CAT[3], capsize=2, linewidth=0.8)
    ax.axhline(30, color=d2d.MUTED, linestyle=":", linewidth=0.9)
    ax.text(70, 31, "30 M/s, Chapter 2's high-activity estimate", fontsize=d2d.FONT_PT - 0.8, color=d2d.INK)
    ax.set_xscale("log", base=2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:,}" for v in x])
    ax.set_xlabel("singles per batch")
    ax.set_ylabel("M singles per second")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
