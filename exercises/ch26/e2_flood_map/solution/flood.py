# SPDX-License-Identifier: MIT
"""Exercise 26.2: a flood map and the crystal lookup table of one detector block.

Many detector blocks do not tell which crystal a photon hit. Light from a crystal spreads over
several photodetectors, and the board reports a position (u, v), each 0 to 1, computed from their
signals (Anger logic). A flood, a uniform irradiation of the block, histogrammed in u and v,
shows one blob per crystal, but not on a regular grid: the light sharing compresses the edge
crystals together and bends the rows. The crystal lookup table (LUT) gives, for every pixel of
the flood, the crystal its events belong to.

MiniDAQ's boards identify crystals themselves (Chapter 9), so this step runs on the board's
side; the exercise is what a board's calibration does, and what you are reviewing when you read
it.
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


# [snippet:peaks]
def find_peaks(img, n=SIDE * SIDE, radius=2):
    """The n strongest local maxima of the smoothed flood, as (row, column) positions in pixels.
    A local maximum is a pixel no lower than every pixel within `radius`: that keeps one pixel
    per blob, where the n highest pixels would all be on the brightest blobs."""
    s = smooth(img)
    pad = np.pad(s, radius, mode="constant", constant_values=-1.0)
    best = np.full_like(s, -1.0)
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dr or dc:
                shifted = pad[radius + dr:radius + dr + s.shape[0],
                              radius + dc:radius + dc + s.shape[1]]
                best = np.maximum(best, shifted)
    rows, cols = np.nonzero(s >= best)
    order = np.argsort(s[rows, cols])[::-1][:n]
    rows, cols = rows[order], cols[order]
    # Between pixels: the centroid of the 3 x 3 pixels around each maximum, and + 0.5 because
    # pixel k covers positions k to k + 1.
    padded = np.pad(s, 1)
    w = np.stack([padded[rows + 1 + dr, cols + 1 + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1)])
    dr = np.repeat([-1, 0, 1], 3)[:, None]
    dc = np.tile([-1, 0, 1], 3)[:, None]
    total = w.sum(0)
    return np.stack([rows + (w * dr).sum(0) / total, cols + (w * dc).sum(0) / total], 1) + 0.5
# [/snippet:peaks]


# [snippet:order]
def arrange(peaks, side=SIDE):
    """The peaks as a side x side grid, [row][column] of the crystals: the side peaks highest in
    the flood are the first row, and so on, each row ordered by column. Rows bend and the edges
    are compressed, so no fixed spacing works; only the order does."""
    if len(peaks) != side * side:
        raise ValueError(f"{len(peaks)} peaks, {side * side} expected")
    by_row = peaks[np.argsort(peaks[:, 0], kind="stable")]
    grid = by_row.reshape(side, side, 2)
    for r in range(side):
        grid[r] = grid[r][np.argsort(grid[r][:, 1], kind="stable")]
    return grid
# [/snippet:order]


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
