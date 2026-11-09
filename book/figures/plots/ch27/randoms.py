# SPDX-License-Identifier: MIT
"""Figure for Chapter 27: three randoms estimates against the simulator's truth in the patient-like
scan, from section 2 of measurements/ch27/corrections.txt.

    python3 book/tools/figures.py build book/figures/plots/ch27/randoms.py screen 6 pdf measurements/ch27/corrections.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch27/corrections.txt"
ROW = re.compile(r"^\| (delayed window|2 tau S_a S_b / t, all singles|the same, singles in a prompt coincidence subtracted) \| ([\d,]+) \| ([+-][\d.]+)% \|")
NAMES = {"delayed window": "delayed window",
         "2 tau S_a S_b / t, all singles": "from the singles,\nall of them",
         "the same, singles in a prompt coincidence subtracted": "from the singles,\npaired ones subtracted"}


def main(dst):
    rows = [(m.group(1), int(m.group(2).replace(",", "")), float(m.group(3))) for m in map(ROW.match, SRC.read_text().splitlines()) if m]
    truth = re.search(r"randoms ([\d,]+) \(", SRC.read_text()).group(1)
    fig, ax = d2d.figure(height=1.7, width=0.75)
    y = list(range(len(rows)))[::-1]
    for yi, (name, n, err) in zip(y, rows):
        c = d2d.CAT[2] if abs(err) < 3 else (d2d.CAT[0] if abs(err) < 10 else d2d.MUTED)
        ax.barh(yi, err, color=c, height=0.55)
        ax.text(max(err, 0) + 1, yi, f"{err:+.1f}%  ({n:,})", va="center",
                ha="left", fontsize=d2d.FONT_PT - 1, color=d2d.INK)
    ax.axvline(0, color=d2d.INK, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([NAMES[r[0]] for r in rows])
    ax.set_xlim(-12, 48)
    ax.set_xlabel(f"estimate against the true randoms ({truth}), %")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
