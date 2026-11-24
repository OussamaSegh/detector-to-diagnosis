# SPDX-License-Identifier: MIT
"""Figure for Chapter 26, Exercise 26.2: the flood map of a 16 x 16 block and its crystal lookup
table, made with the exercise's own solution (exercises/ch26/e2_flood_map/solution/flood.py) on the
synthetic flood of its acceptance tests: each crystal on a regular grid, the light sharing's
distortion, here a little stronger than in the tests (edges compressed by 0.3, rows bent by 0.012)
and blurrier (1.6 pixels), 800 events per crystal, seed 26. Left: the flood. Middle: the peaks found and their order, row by
row. Right: the lookup table's regions over the flood.

    python3 book/tools/figures.py build book/figures/plots/ch26/floodmap.py screen 6 pdf exercises/ch26/e2_flood_map
"""
import pathlib
import sys

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "exercises/ch26/e2_flood_map/solution"))
import flood as f  # noqa: E402

PIXELS = 256


def block(rng, events_per_crystal=400, blur_px=1.0, compress=0.25, bend=0.01):
    """The flood of the exercise's tests (tests/test_flood.py, block())."""
    side = f.SIDE
    q = (np.arange(side) + 0.5) / side - 0.5
    qr, qc = np.meshgrid(q, q, indexing="ij")

    def distort(a):
        return a * (1 - compress * (2 * a) ** 2)

    row = 0.5 + distort(qr) + bend * (2 * qc) ** 2
    col = 0.5 + distort(qc)
    crystal = np.repeat(np.arange(side * side), events_per_crystal)
    blur = blur_px / PIXELS
    v = row.reshape(-1)[crystal] + rng.normal(0, blur, crystal.size)
    u = col.reshape(-1)[crystal] + rng.normal(0, blur, crystal.size)
    return u, v


def main(dst):
    rng = np.random.default_rng(26)
    u, v = block(rng, events_per_crystal=800, blur_px=1.6, compress=0.3, bend=0.012)
    img = f.flood(u, v, PIXELS)
    grid = f.arrange(f.find_peaks(img))
    table = f.lut(grid, PIXELS)
    fig, axes = d2d.figure(height=2.2, width=1.0, ncols=3)
    show = np.sqrt(img)  # square root: the dim gaps between blobs stay visible
    ext = (0, PIXELS, PIXELS, 0)
    for ax in axes:
        ax.imshow(show, cmap=d2d.CMAP, extent=ext, interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("u", fontsize=d2d.FONT_PT - 1)
    axes[0].set_ylabel("v", fontsize=d2d.FONT_PT - 1)
    axes[0].set_title("the flood: one blob per crystal", fontsize=d2d.FONT_PT - 0.6, color=d2d.INK)
    for r in range(f.SIDE):
        axes[1].plot(grid[r, :, 1], grid[r, :, 0], color="white", lw=0.6)
    axes[1].scatter(grid[..., 1].ravel(), grid[..., 0].ravel(), s=3, color=d2d.CAT[1], zorder=3)
    axes[1].set_title("peaks found, joined row by row", fontsize=d2d.FONT_PT - 0.6, color=d2d.INK)
    edges = (np.diff(table, axis=0, prepend=table[:1]) != 0) | (np.diff(table, axis=1, prepend=table[:, :1]) != 0)
    over = np.zeros((PIXELS, PIXELS, 4))
    over[edges] = (1, 1, 1, 0.9)
    axes[2].imshow(over, extent=ext, interpolation="nearest")
    axes[2].set_title("lookup table: pixel to crystal", fontsize=d2d.FONT_PT - 0.6, color=d2d.INK)
    for ax in axes:
        ax.set_xlim(14, PIXELS - 14)
        ax.set_ylim(PIXELS - 14, 14)
    fig.tight_layout(pad=0.3, w_pad=0.6)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
