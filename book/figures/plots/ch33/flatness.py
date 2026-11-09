# SPDX-License-Identifier: MIT
"""Figure for Chapter 33: the end-to-end image checks over five seeds, with and without attenuation
correction, against the limits of tools/e2e.py, from measurements/ch33/flatness.txt.

    python3 book/tools/figures.py build book/figures/plots/ch33/flatness.py screen 8 pdf measurements/ch33/flatness.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch33/flatness.txt"


def main(dst):
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in SRC.read_text().splitlines() if l.startswith("| ") and l[2].isdigit()]
    fig, (ax, bx) = d2d.figure(height=1.9, width=1.0, ncols=2)
    seeds = [int(r[0]) for r in rows]
    for a, ki, kn, lo, hi, lab in ((ax, 2, 4, 78, 82, "radius at half level, mm"), (bx, 3, 5, 0.9, 1.1, "centre over periphery")):
        val = lambda v: float(v.replace(" mm", ""))  # noqa: E731
        a.axhspan(lo, hi, color=d2d.tint(d2d.CAT[2], 0.18), lw=0)
        a.plot(seeds, [val(r[ki]) for r in rows], color=d2d.PART, marker="o", ms=4, lw=0, label="attenuation corrected")
        a.plot(seeds, [val(r[kn]) for r in rows], color=d2d.MUTED, marker="s", ms=4, lw=0, label="not corrected")
        a.set_xticks(seeds)
        a.set_xlabel("seed")
        a.set_ylabel(lab)
    ax.set_ylim(77.5, 83.5)
    bx.set_ylim(0.55, 1.15)
    ax.text(32.6, 78.1, "accepted: within 2 mm of 80", fontsize=d2d.FONT_PT - 1.2, color=d2d.CAT[2])
    bx.text(34.3, 0.91, "accepted: within 0.1 of 1", fontsize=d2d.FONT_PT - 1.2, color=d2d.CAT[2])
    bx.legend(loc="lower left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
