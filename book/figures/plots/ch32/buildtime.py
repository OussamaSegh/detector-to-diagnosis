# SPDX-License-Identifier: MIT
"""Figure for Chapter 32: where the build time goes. A clean build, a build with nothing to do, and
the rebuild after touching each of four files, with the number of commands each ran, from
measurements/ch32/build-times.txt.

    python3 book/tools/figures.py build book/figures/plots/ch32/buildtime.py screen 7 pdf measurements/ch32/build-times.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch32/build-times.txt"
ROW = re.compile(r"^(clean build of every target|build with nothing to do|after touching \S+):\s+([\d.]+) s, (\d+) commands")


def main(dst):
    rows = [(m.group(1), float(m.group(2)), int(m.group(3))) for m in map(ROW.match, SRC.read_text().splitlines()) if m]
    fig, ax = d2d.figure(height=2.0, width=0.85)
    y = list(range(len(rows)))[::-1]
    for yi, (name, t, n) in zip(y, rows):
        c = d2d.MUTED if name.startswith(("clean", "build")) else d2d.PART
        ax.barh(yi, t, color=c, height=0.6)
        ax.text(t + 2, yi, f"{t:.1f} s, {n} commands", va="center", fontsize=d2d.FONT_PT - 1.1, color=d2d.INK)
    labels = [r[0].replace("after touching ", "touch ").replace("minidaq/include/minidaq/", "").replace("minidaq/src/", "").replace("minidaq/apps/", "")
              for r in rows]
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 210)
    ax.set_xlabel("s, release preset, 4 jobs, Ninja")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
