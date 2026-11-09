# SPDX-License-Identifier: MIT
"""Figure for Chapter 27: the decay factor of a 10-minute fluorine-18 frame against its start, exact
and to the frame's start alone (left), and the live fractions of a block and of a coincidence for a
non-paralyzable dead time of 200 ns, with the measured point at 109 kHz per block from section 5 of
measurements/ch27/corrections.txt (right).

    python3 book/tools/figures.py build book/figures/plots/ch27/factors.py screen 6 pdf measurements/ch27/corrections.txt
"""
import math
import pathlib
import re
import sys

import numpy as np

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch27/corrections.txt"
HALF_LIFE = 109.77
TAU = 200e-9


def main(dst):
    text = SRC.read_text()
    rate = float(re.search(r"Recorded singles per block: (\d+) kHz", text).group(1)) * 1e3
    single = float(re.search(r"\| Singles live fraction \| ([\d.]+) \|", text).group(1))
    coinc = float(re.search(r"\| Coincidence live fraction \(trues\) \| ([\d.]+) \|", text).group(1))
    lam = math.log(2) / HALF_LIFE
    fig, (ax, bx) = d2d.figure(height=2.0, width=1.0, ncols=2)
    t0 = np.linspace(0, 120, 200)
    T = 10.0
    exact = np.exp(lam * t0) * lam * T / -np.expm1(-lam * T)
    start = np.exp(lam * t0)
    ax.plot(t0, exact, color=d2d.PART, lw=d2d.LINE_PT * 1.4, label="exact, over the frame")
    ax.plot(t0, start, color=d2d.CAT[0], lw=d2d.LINE_PT, ls="--", label="to the frame's start only")
    e60 = math.exp(lam * 60) * lam * T / -math.expm1(-lam * T)
    ax.scatter([60, 60], [e60, math.exp(lam * 60)], color=[d2d.PART, d2d.CAT[0]], s=14, zorder=3)
    ax.annotate(f"{e60:.4f}", (60, e60), xytext=(30, 1.75), fontsize=d2d.FONT_PT - 1, color=d2d.PART,
                arrowprops={"arrowstyle": "-", "color": d2d.MUTED, "lw": 0.6})
    ax.annotate(f"{math.exp(lam * 60):.4f}, 3.1% low", (60, math.exp(lam * 60)), xytext=(68, 1.15), fontsize=d2d.FONT_PT - 1,
                color=d2d.CAT[0], arrowprops={"arrowstyle": "-", "color": d2d.MUTED, "lw": 0.6})
    ax.set_xlabel("frame start after the reference, min")
    ax.set_ylabel("decay factor, 10 min frame")
    ax.set_title("decay, fluorine-18", fontsize=d2d.FONT_PT, color=d2d.INK)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    m = np.linspace(0, 1.0e6, 200)
    bx.plot(m / 1e3, 1 - m * TAU, color=d2d.CAT[0], lw=d2d.LINE_PT, label="a block")
    bx.plot(m / 1e3, (1 - m * TAU) ** 2, color=d2d.PART, lw=d2d.LINE_PT * 1.4, label="a coincidence (both blocks)")
    bx.scatter([rate / 1e3, rate / 1e3], [single, coinc], color=d2d.INK, s=14, zorder=3)
    bx.annotate(f"measured, {rate / 1e3:.0f} kHz:\n{single:.3f} and {coinc:.3f}", (rate / 1e3, coinc), xytext=(380, 0.955),
                fontsize=d2d.FONT_PT - 1, color=d2d.INK, arrowprops={"arrowstyle": "-", "color": d2d.MUTED, "lw": 0.6})
    bx.set_xlabel("recorded singles per block, kHz")
    bx.set_ylabel("live fraction")
    bx.set_ylim(0.6, 1.01)
    bx.set_title("dead time, 200 ns non-paralyzable", fontsize=d2d.FONT_PT, color=d2d.INK)
    bx.legend(loc="lower left", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
