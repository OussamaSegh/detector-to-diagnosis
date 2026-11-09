# SPDX-License-Identifier: MIT
"""Figure for Chapter 18: mutation testing of the coincidence sorter, three runs, from the summary
line of each report in measurements/ch18.

    python3 book/tools/figures.py build book/figures/plots/ch18/mutation.py screen 4 pdf measurements/ch18
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch18"
RUNS = [("mutation-sorter-examples.txt", "example tests"), ("mutation-sorter-properties.txt", "+ properties"),
        ("mutation-sorter-final.txt", "+ three tests for\nthe survivors")]
SUMMARY = re.compile(r"# killed (\d+), timeout (\d+), survived (\d+), invalid (\d+); mutation score ([\d.]+)%")


def main(dst):
    fig, ax = d2d.figure(height=1.75, width=0.8)
    for y, (name, label) in enumerate(reversed(RUNS)):
        k, t, s, _, score = SUMMARY.search((SRC / name).read_text().splitlines()[-1]).groups()
        k, t, s = int(k), int(t), int(s)
        ax.barh(y, k, color=d2d.CAT[2], height=0.62, label="killed" if y == 0 else None)
        ax.barh(y, t, left=k, color=d2d.tint(d2d.CAT[2], 0.5), hatch="////", edgecolor="white", linewidth=0.3, height=0.62,
                label="timeout (counts as killed)" if y == 0 else None)
        ax.barh(y, s, left=k + t, color=d2d.SEM["mistakes"], height=0.62, hatch="....", edgecolor="white", linewidth=0.3,
                label="survived" if y == 0 else None)
        ax.text(k + t + s + 1.5, y, f"{score}%  ({s} survive)", va="center", fontsize=d2d.FONT_PT - 0.8)
    ax.set_yticks(range(len(RUNS)))
    ax.set_yticklabels([r[1] for r in reversed(RUNS)])
    ax.set_xlim(0, 215)
    ax.set_xlabel("164 compiling mutants of coincidence_sorter.cpp (7 more do not compile)")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, 1.32), ncol=3, frameon=False, fontsize=d2d.FONT_PT - 0.9)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
