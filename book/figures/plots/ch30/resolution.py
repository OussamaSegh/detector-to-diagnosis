# SPDX-License-Identifier: MIT
"""Figure for Chapter 30: spatial resolution of point sources in air. Left, FBP: radial and
tangential FWHM against the point's distance from the axis, for 0.25 mm and 2 mm pixels (section
1). Right, OSEM: the same widths against the iteration, 0.5 mm pixels, with FBP's for comparison
(section 2). From measurements/ch30/quality.txt.

    python3 book/tools/figures.py build book/figures/plots/ch30/resolution.py screen 6 pdf measurements/ch30/quality.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch30/quality.txt"


def table(text):
    rows = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")]
    return [[c.strip() for c in r.split("|")[1:-1]] for r in rows[1:]]


def mm(v):
    return float(v.replace(" mm", ""))


def main(dst):
    text = SRC.read_text()
    fbp = table(text.split("## 1.")[1].split("## 2.")[0])
    osem = table(text.split("## 2.")[1].split("## 2b.")[0])
    fig, (ax, bx) = d2d.figure(height=2.1, width=1.0, ncols=2)
    for j, pix in enumerate(["0.25 mm", "2 mm"]):
        rows = [r for r in fbp if r[1] == pix and r[0] in ("10 mm", "50 mm", "100 mm")]
        pos = [mm(r[0]) for r in rows]
        c = d2d.PART if j == 0 else d2d.CAT[0]
        ax.plot(pos, [mm(r[2]) for r in rows], color=c, marker="o", ms=3.5, lw=d2d.LINE_PT, label=f"radial, {pix} pixels")
        ax.plot(pos, [mm(r[4]) for r in rows], color=c, marker="s", ms=3.5, lw=d2d.LINE_PT, ls="--",
                label=f"tangential, {pix} pixels")
    ax.set_xlabel("point's distance from the axis, mm")
    ax.set_ylabel("FWHM, mm")
    ax.set_title("FBP", fontsize=d2d.FONT_PT, color=d2d.INK)
    ax.set_ylim(0, 8.5)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.4, frameon=False)
    iters = [1, 2, 4, 8, 16, 32]
    for k, pos in enumerate(["10 mm", "50 mm", "100 mm"]):
        c = [d2d.PART, d2d.CAT[0], d2d.CAT[2]][k]
        for kind, ls, mk in (("radial FWHM", "-", "o"), ("tangential FWHM", "--", "s")):
            r = next(r for r in osem if r[0] == pos and r[1] == kind)
            bx.plot(iters, [float(v) for v in r[2:8]], color=c, ls=ls, marker=mk, ms=3, lw=d2d.LINE_PT)
            bx.scatter([50], [float(r[8])], color=c, marker=mk, s=14, facecolors="none")
        bx.text(1.1, {"10 mm": 0.75, "50 mm": 2.9, "100 mm": 5.7}[pos], f"point at {pos}", fontsize=d2d.FONT_PT - 1.2, color=c)
    bx.set_xscale("log", base=2)
    bx.set_xticks(iters + [50])
    bx.set_xticklabels([str(i) for i in iters] + ["FBP"])
    bx.minorticks_off()
    bx.set_xlabel("OSEM iteration (8 subsets)")
    bx.set_title("OSEM, 0.5 mm pixels: solid radial, dashed tangential", fontsize=d2d.FONT_PT - 0.5, color=d2d.INK)
    bx.set_ylim(0, 8.5)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
