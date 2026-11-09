# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: fixed and per-single coincidence windows, and the
delayed window, on one short stream of singles.

    python3 book/tools/figures.py build book/figures/plots/ch10/windows.py screen 2 pdf

The window is 4 ns as in MiniDAQ; the delay is shortened to 20 ns so that the
delayed windows fit on the same axis (MiniDAQ's default is 100 ns).
"""
import sys

import matplotlib.pyplot as plt

import d2d

WINDOW = 4.0
DELAY = 20.0
SINGLES = [0.0, 2.5, 3.5, 6.0, 12.0, 14.5, 21.5, 26.0, 33.5, 37.0]
COLORS = {1: d2d.MUTED, 2: d2d.CAT[0], 3: d2d.CAT[3]}  # alone, pair, multiple


def fixed_windows(ts):
    out, i = [], 0
    while i < len(ts):
        j = i + 1
        while j < len(ts) and ts[j] - ts[i] <= WINDOW:
            j += 1
        out.append((i, j))
        i = j
    return out


def per_single_windows(ts):
    out = []
    for i in range(len(ts)):
        j = i + 1
        while j < len(ts) and ts[j] - ts[i] <= WINDOW:
            j += 1
        out.append((i, j))
    return out


def draw_row(ax, y, windows, ts, stagger):
    for k, (i, j) in enumerate(windows):
        n = min(j - i, 3)
        dy = -(k % 3) * 0.15 if stagger else 0.0
        ax.add_patch(plt.Rectangle((ts[i], y - 0.12 + dy), WINDOW, 0.12, color=COLORS[n], alpha=0.35, linewidth=0))
        ax.plot([ts[i]], [y - 0.06 + dy], "|", color=COLORS[n], markersize=7)


def main(dst):
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    rows = {"fixed": 2.2, "per single": 1.2, "delayed, D = 20 ns\n(fixed openers)": 0.0}
    for y in rows.values():
        ax.axhline(y + 0.25, color=d2d.RULE, linewidth=0.6)
        ax.plot(SINGLES, [y + 0.25] * len(SINGLES), "o", color=d2d.INK, markersize=3)
    draw_row(ax, rows["fixed"] + 0.12, fixed_windows(SINGLES), SINGLES, False)
    draw_row(ax, rows["per single"] + 0.12, per_single_windows(SINGLES), SINGLES, True)
    y = rows["delayed, D = 20 ns\n(fixed openers)"] + 0.12
    for i, _ in fixed_windows(SINGLES):
        start = SINGLES[i] + DELAY
        if start > 40:
            continue
        hits = [t for t in SINGLES if start <= t <= start + WINDOW]
        color = COLORS[2] if len(hits) == 1 else COLORS[1] if not hits else COLORS[3]
        ax.add_patch(plt.Rectangle((start, y - 0.12), WINDOW, 0.12, color=color, alpha=0.35, linewidth=0))
        ax.plot([SINGLES[i]], [y - 0.06], "|", color=d2d.MUTED, markersize=7)
        ax.annotate("", xy=(start, y - 0.02), xytext=(SINGLES[i], y - 0.02),
                    arrowprops={"arrowstyle": "->", "color": d2d.MUTED, "linewidth": 0.6,
                                "connectionstyle": "arc3,rad=0.25"})
    ax.set_yticks([v + 0.15 for v in rows.values()])
    ax.set_yticklabels(list(rows.keys()))
    ax.set_xlim(-1, 42)
    ax.set_ylim(-0.5, 2.75)
    ax.set_xlabel("time (ns)")
    for n, label in ((2, "two singles: a pair"), (3, "three or more: a multiple"), (1, "one single, or none")):
        ax.plot([], [], "s", color=COLORS[n], alpha=0.5, label=label)
    ax.legend(loc="upper right", frameon=False, ncol=3, bbox_to_anchor=(1.0, 1.13))
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
