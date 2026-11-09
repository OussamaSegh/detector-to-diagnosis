# SPDX-License-Identifier: MIT
"""Figure for Chapter 24: how long a stop takes, from the stop command to configured, five runs per
scenario (min, median, max), with the slow control's 100 ms cycles marked, from
measurements/ch24/run_sequence.txt.

    python3 book/tools/figures.py build book/figures/plots/ch24/stops.py screen 5 pdf measurements/ch24/run_sequence.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch24/run_sequence.txt"
ROW = re.compile(r"^\| ([^|]+?) \| (\d+) / (\d+) / (\d+) \|.*\| (\d) of 5 \|$")


def main(dst):
    rows = [m.groups() for m in map(ROW.match, SRC.read_text().splitlines()) if m]
    fig, ax = d2d.figure(height=1.9, width=0.8)
    for y, (name, lo, med, hi, ok) in enumerate(reversed(rows)):
        lo, med, hi, ok = int(lo), int(med), int(hi), int(ok)
        c = d2d.CAT[2] if ok == 5 else d2d.SEM["mistakes"]
        ax.plot([lo, hi], [y, y], color=d2d.tint(c, 0.5), linewidth=4, solid_capstyle="round")
        ax.scatter(med, y, color=c, s=24, zorder=3, marker="o" if ok == 5 else "X")
        ax.text(hi + 12, y, f"{med} ms, {ok} of 5 complete", va="center", fontsize=d2d.FONT_PT - 1.1)
    for k in (1, 2):
        ax.axvline(100 * k + 20, color=d2d.MUTED, linestyle=":", linewidth=0.8)
    ax.text(122, len(rows) - 0.45, "one and two slow-control cycles", fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED, va="bottom")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=d2d.FONT_PT - 0.9)
    ax.set_xlim(0, 760)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlabel("stop command to configured (ms)")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
