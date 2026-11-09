# SPDX-License-Identifier: MIT
"""Figure for Chapter 28: OSEM iteration by iteration on the phantom of hot rods. Left, the
log-likelihood and the background noise; right, contrast recovery against noise for the three rods,
and what a Gaussian post-filter does at iterations 4 and 32. From sections 2 and 5 of
measurements/ch28/reconstruct.txt.

    python3 book/tools/figures.py build book/figures/plots/ch28/crc.py screen 6 pdf measurements/ch28/reconstruct.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch28/reconstruct.txt"


def table(text):
    rows = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("|---")]
    return [[c.strip() for c in r.split("|")[1:-1]] for r in rows[1:]]


def main(dst):
    text = SRC.read_text()
    it = table(text.split("## 2.")[1].split("## 2b.")[0])
    filt = table(text.split("## 5.")[1])
    iters = [int(r[0]) for r in it]
    ll = [float(r[1].replace(",", "")) for r in it]
    cov = [float(r[2].rstrip("%")) for r in it]
    crc = [[float(r[k]) for r in it] for k in (3, 4, 5)]
    fig, (ax, bx) = d2d.figure(height=2.1, width=1.0, ncols=2)
    ax.plot(iters, ll, color=d2d.PART, marker="o", ms=3, lw=d2d.LINE_PT * 1.3)
    ax.set_xlabel("iteration (8 subsets)")
    ax.set_ylabel("log-likelihood over iteration 1", color=d2d.PART)
    ax2 = ax.twinx()
    ax2.plot(iters, cov, color=d2d.CAT[0], marker="s", ms=3, ls="--", lw=d2d.LINE_PT)
    ax2.set_ylabel("background noise, %", color=d2d.CAT[0])
    ax2.grid(False)
    ax2.set_ylim(0, 90)
    d2d.label(ax, 2.5, 5300, "likelihood keeps rising", d2d.PART)
    d2d.label(ax, 14, 1600, "noise keeps rising too", d2d.CAT[0])
    names = ["12 mm rod", "8 mm rod", "5 mm rod"]
    for k in range(3):
        bx.plot(cov, crc[k], color=d2d.CAT[k] if k else d2d.PART, marker=d2d.MARKERS[k], ms=3,
                ls=d2d.DASHES[k], lw=d2d.LINE_PT, label=names[k])
    for r in filt:
        if "Gaussian" in r[0]:
            c = float(r[1].rstrip("%"))
            bx.scatter([c] * 3, [float(r[2]), float(r[3]), float(r[4])], facecolors="none",
                       edgecolors=[d2d.PART, d2d.CAT[1], d2d.CAT[2]], s=18, zorder=3)
    bx.axhline(1, color=d2d.INK, lw=0.6)
    bx.text(30, 0.3, "hollow: Gaussian post-filter,\n4 or 6 mm FWHM", fontsize=d2d.FONT_PT - 1.3, color=d2d.MUTED)
    bx.set_xlabel("background noise (CoV), %")
    bx.set_ylabel("contrast recovery")
    bx.set_ylim(0.2, 1.4)
    bx.legend(loc="lower right", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
