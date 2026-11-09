# SPDX-License-Identifier: MIT
"""Figure for Chapter 28: the background's radial profile when a correction is left out of the
reconstruction's model, from section 4 of measurements/ch28/reconstruct.txt. A correct model is
flat at 1.

    python3 book/tools/figures.py build book/figures/plots/ch28/model.py screen 6 pdf measurements/ch28/reconstruct.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch28/reconstruct.txt"
SHOW = {"all corrections": (d2d.PART, 1.6), "no attenuation": (None, 1), "no scatter": (None, 1),
        "no normalization": (None, 1), "none": (None, 1)}


def main(dst):
    text = SRC.read_text().split("## 4.")[1].split("## 5.")[0]
    rows = [[c.strip() for c in l.split("|")[1:-1]] for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")]
    rings = [h.replace(" mm", "") for h in rows[0][1:-1]]
    x = [int(r.split(" to ")[0]) + 5 for r in rings]
    fig, ax = d2d.figure(height=2.0, width=0.8)
    k = 0
    for r in rows[1:]:
        if r[0] not in SHOW:
            continue
        c, lw = SHOW[r[0]]
        c = c or [d2d.CAT[0], d2d.CAT[2], d2d.CAT[3], d2d.MUTED][k]
        vals = [float(v) for v in r[1:-1]]
        ax.plot(x, vals, color=c, marker=d2d.MARKERS[k % len(d2d.MARKERS)], ms=3.5, lw=d2d.LINE_PT * lw,
                ls="-" if r[0] == "all corrections" else d2d.DASHES[k], label=f"{r[0]} (CRC 12 mm {r[-1]})")
        if r[0] != "all corrections":
            k += 1
    ax.axhline(1, color=d2d.INK, lw=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r} mm" for r in rings])
    ax.set_xlabel("ring of the background, distance from the axis")
    ax.set_ylabel("ring mean / mean of the rings")
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.3, frameon=False)
    ax.set_ylim(0.6, 1.75)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
