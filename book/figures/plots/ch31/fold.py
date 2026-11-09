# SPDX-License-Identifier: MIT
"""Figure for Chapter 31: the time difference that does not fold. Prompts of a centred point source,
drawn with a fixed seed: a timing peak of 300 ps FWHM on a flat randoms background, histogrammed as
MDQ-L1's dt_ps (later minus earlier, never negative) and as the signed difference (lower-numbered
crystal minus higher-numbered).

    python3 book/tools/figures.py build book/figures/plots/ch31/fold.py screen 7 pdf
"""
import sys

import numpy as np

import d2d


def main(dst):
    rng = np.random.default_rng(31)
    n = 135_000
    signed = np.concatenate([rng.normal(0, 300 / 2.3548, int(n * 0.95)), rng.uniform(-2000, 2000, int(n * 0.05))])
    folded = np.abs(signed)
    bins = np.arange(-1000, 1001, 20)
    fig, ax = d2d.figure(height=1.9, width=0.8)
    hs, _ = np.histogram(signed, bins)
    hf, _ = np.histogram(folded, bins)
    ax.step(bins[:-1], hf, where="post", color=d2d.MUTED, lw=d2d.LINE_PT, label="dt_ps as stored: folded, never negative")
    ax.step(bins[:-1], hs, where="post", color=d2d.PART, lw=d2d.LINE_PT * 1.4, label="signed: lower crystal minus higher")
    half = hs.max() / 2
    ax.annotate("", xy=(-150, half), xytext=(150, half), arrowprops={"arrowstyle": "<->", "color": d2d.PART, "lw": 0.8})
    ax.text(-960, half, "FWHM 300 ps: the CTR", fontsize=d2d.FONT_PT - 1, color=d2d.PART, va="center")
    ax.text(260, hf.max() * 0.93, "twice as high, half as wide,\nno centre to measure", fontsize=d2d.FONT_PT - 1, color=d2d.INK)
    ax.set_xlabel("time difference, ps")
    ax.set_ylabel("prompts per 20 ps")
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(0, hf.max() * 1.25)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.3, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
