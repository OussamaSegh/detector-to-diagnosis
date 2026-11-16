# SPDX-License-Identifier: MIT
"""Figure for Chapter 40: MiniDAQ's problem reports per 100 commits in each release window, with
the u-chart's mean and upper control limits, from measurements/ch40/trends.txt.

    python3 book/tools/figures.py build book/figures/plots/ch40/uchart.py screen 10 pdf measurements/ch40/trends.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch40/trends.txt"
MEAN = re.compile(r"^Mean rate: ([\d.]+) reports per 100 commits")
ROW = re.compile(r"^\| ([\d.]+|unreleased) \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| (above)? *\|")


def main(dst):
    text = SRC.read_text()
    mean = next(float(m.group(1)) for m in map(MEAN.match, text.splitlines()) if m)
    rows = [m.groups() for m in map(ROW.match, text.splitlines()) if m]
    names = [r[0] if r[0] != "unreleased" else "2.0-dev" for r in rows]
    rate = [float(r[3]) for r in rows]
    limit = [float(r[4]) for r in rows]
    x = list(range(len(rows)))
    fig, ax = d2d.figure(height=2.4)
    ax.step(x, limit, where="mid", color=d2d.SEM["mistakes"], linestyle="--", linewidth=0.9)
    ax.axhline(mean, color=d2d.MUTED, linestyle=":", linewidth=0.9)
    ax.text(len(x) - 0.4, mean, f"mean {mean:.1f}", fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED,
            va="bottom", ha="right")
    ax.text(len(x) - 0.4, limit[-1] + 1.0, "upper limit", fontsize=d2d.FONT_PT - 1.2,
            color=d2d.SEM["mistakes"], va="bottom", ha="right")
    for k, (r, row) in enumerate(zip(rate, rows)):
        above = row[5] == "above"
        ax.bar(k, r, width=0.62, color=d2d.SEM["mistakes"] if above else d2d.PART, zorder=2)
        ax.text(k, r + 1.0, row[2], fontsize=d2d.FONT_PT - 1.4, ha="center", va="bottom",
                color=d2d.INK)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.set_ylim(0, max(max(rate), max(limit)) * 1.15)
    ax.set_xlabel("release window (the number on each bar: reports)")
    ax.set_ylabel("reports per 100 commits")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
