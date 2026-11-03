# SPDX-License-Identifier: MIT
"""Exercise 26.2: a flood map and the crystal lookup table of one detector block.

Many detector blocks do not tell which crystal a photon hit. Light from a crystal spreads over
several photodetectors, and the board reports a position (u, v), each 0 to 1, computed from their
signals (Anger logic). A flood, a uniform irradiation of the block, histogrammed in u and v,
shows one blob per crystal, but not on a regular grid: the light sharing compresses the edge
crystals together and bends the rows. The crystal lookup table (LUT) gives, for every pixel of
the flood, the crystal its events belong to.

flood(), smooth(), lut() and identify() are given and correct. TODO: find_peaks() and arrange().
"""
import numpy as np

SIDE = 16  # crystals per block side: 16 x 16


def flood(u, v, pixels=256):
    """The flood map: counts per pixel, rows v and columns u, both 0 to 1."""
    iu = np.clip((np.asarray(u) * pixels).astype(int), 0, pixels - 1)
    iv = np.clip((np.asarray(v) * pixels).astype(int), 0, pixels - 1)
    return np.bincount(iv * pixels + iu, minlength=pixels * pixels).reshape(pixels, pixels)


def smooth(img, sigma=1.0):
    """A Gaussian blur, one axis after the other."""
    r = int(np.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda row: np.convolve(row, k, mode="same"), 1, img.astype(float))
    return np.apply_along_axis(lambda col: np.convolve(col, k, mode="same"), 0, out)


def find_peaks(img, n=SIDE * SIDE, radius=2):
    """The n strongest peaks of the flood, as (row, column) pixel positions."""
    flat = np.argsort(img, axis=None)[::-1][:n]
    rows, cols = np.unravel_index(flat, img.shape)
    return np.stack([rows, cols], 1).astype(float)


def arrange(peaks, side=SIDE):
    """The peaks as a side x side grid, [row][column] of the crystals."""
    pixels = 256
    grid = np.zeros((side, side, 2))
    for r, c in peaks:
        grid[min(side - 1, int(r * side / pixels)), min(side - 1, int(c * side / pixels))] = (r, c)
    return grid


def lut(grid, pixels=256):
    """The crystal (row * side + column) of every pixel: the peak nearest its centre."""
    side = grid.shape[0]
    centres = grid.reshape(-1, 2)
    rr, cc = np.mgrid[0:pixels, 0:pixels]
    best = np.full((pixels, pixels), np.inf)
    out = np.zeros((pixels, pixels), dtype=np.int32)
    for k, (r, c) in enumerate(centres):
        d = (rr + 0.5 - r) ** 2 + (cc + 0.5 - c) ** 2  # pixel k is centred on k + 0.5
        closer = d < best
        best[closer] = d[closer]
        out[closer] = k
    assert out.max() < side * side
    return out


def identify(u, v, table):
    """The crystal of each event (u, v), through the lookup table."""
    pixels = table.shape[0]
    iu = np.clip((np.asarray(u) * pixels).astype(int), 0, pixels - 1)
    iv = np.clip((np.asarray(v) * pixels).astype(int), 0, pixels - 1)
    return table[iv, iu]
