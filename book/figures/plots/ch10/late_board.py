# SPDX-License-Identifier: MIT
"""Figure for Chapter 10: what a board whose singles are lost does to the sinogram.

A uniform cylinder (radius 100 mm) in MiniDAQ's ring (384 crystals, 24 blocks of 16, inner
radius 150 mm): the expected counts of every line of response, binned in (s, phi). On the
right, block 5's singles are all lost (late or out of order), and every line of response
through it is missing: two diagonal bands, not a uniformly lower count.

    python3 book/tools/figures.py build book/figures/plots/ch10/late_board.py screen 2 pdf
"""
import sys

import numpy as np
from matplotlib import patheffects

import d2d

N, PER_BLOCK, R, PHANTOM, FOV = 384, 16, 150.0, 100.0, 120.0
LOST = 5


def sinogram(lost=None):
    th = (np.arange(N) + 0.5) * 2 * np.pi / N
    i, j = np.triu_indices(N, 1)
    phi = ((th[i] + th[j]) / 2) % np.pi
    s = R * np.cos((th[j] - th[i]) / 2)
    flip = ((th[i] + th[j]) / 2) >= np.pi
    s = np.where(flip, -s, s)
    keep = np.abs(s) < FOV
    if lost is not None:
        keep &= (i // PER_BLOCK != lost) & (j // PER_BLOCK != lost)
    w = 2 * np.sqrt(np.clip(PHANTOM ** 2 - s ** 2, 0, None))  # chord through the cylinder
    rng, bins = ((-FOV, FOV), (0, 180)), (64, 90)
    h, _, _ = np.histogram2d(s[keep], np.degrees(phi[keep]), bins=bins, range=rng, weights=w[keep])
    # Divide by the number of lines of response of the full ring in each bin (a normalization):
    # the crystals sample (s, phi) unevenly, which would otherwise show as stripes.
    inside = np.abs(s) < FOV
    n, _, _ = np.histogram2d(s[inside], np.degrees(phi[inside]), bins=bins, range=rng)
    return h / np.maximum(n, 1)


def main(dst):
    fig, axes = d2d.figure(height=2.5, ncols=2, sharey=True)
    full, part = sinogram(), sinogram(LOST)
    vmax = full.max()
    for ax, h, title in ((axes[0], full, "every board in time"),
                         (axes[1], part, f"block {LOST}'s singles lost")):
        ax.imshow(h, origin="lower", aspect="auto", cmap=d2d.CMAP, vmin=0, vmax=vmax,
                  extent=(0, 180, -FOV, FOV), interpolation="nearest")
        ax.set_title(title)
        ax.set_xlabel("angle φ (degrees)")
        ax.grid(False)
        ax.set_xticks([0, 45, 90, 135, 180])
    axes[0].set_ylabel("distance s (mm)")
    axes[1].annotate("lines of response\nthrough block 5", xy=(22, 62), xytext=(62, 72),
                     color=d2d.INK, fontsize=d2d.FONT_PT - 0.6, ha="left",
                     bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85},
                     arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.9,
                                   "path_effects": [patheffects.withStroke(linewidth=2.4, foreground="white")]})
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
