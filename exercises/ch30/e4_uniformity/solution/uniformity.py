# SPDX-License-Identifier: MIT
"""Exercise 30.4, a solution: the uniformity of an image of a uniform cylinder.

Two numbers, as the uniformity tests of nuclear medicine define them (NEMA's for gamma cameras,
used here on a transverse slice of a PET image of a uniform cylinder):

- integral uniformity, 100 (max - min) / (max + min) over the region;
- differential uniformity, the largest 100 (max - min) / (max + min) of any five consecutive
  pixels of a row or a column inside the region.

Both on the image smoothed once with the nine-point kernel [1 2 1; 2 4 2; 1 2 1] / 16, and only
over pixels whose whole neighborhood lies inside the region: the edge of the cylinder is blurred
by the resolution, and is not part of what uniformity measures.
"""
import numpy as np

KERNEL = np.array([[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]]) / 16.0


def central_region(shape, center, radius_px, fraction=0.75):
    """The pixels within `fraction` of the cylinder's radius of its center (the central field)."""
    yy, xx = np.indices(shape)
    return np.hypot(xx - center[0], yy - center[1]) <= fraction * radius_px


def smooth(img):
    """The image convolved with KERNEL; the outermost pixels, which lack neighbors, are NaN."""
    img = np.asarray(img, dtype=float)
    out = np.full(img.shape, np.nan)
    acc = np.zeros((img.shape[0] - 2, img.shape[1] - 2))
    for dy in range(3):
        for dx in range(3):
            acc += KERNEL[dy, dx] * img[dy:dy + acc.shape[0], dx:dx + acc.shape[1]]
    out[1:-1, 1:-1] = acc
    return out


def _usable(region):
    """The region's pixels whose 3 x 3 neighborhood is inside the region too."""
    r = np.asarray(region, dtype=bool)
    ok = np.zeros_like(r)
    inner = np.ones((r.shape[0] - 2, r.shape[1] - 2), dtype=bool)
    for dy in range(3):
        for dx in range(3):
            inner &= r[dy:dy + inner.shape[0], dx:dx + inner.shape[1]]
    ok[1:-1, 1:-1] = inner
    return ok


def _spread(v):
    return 100.0 * (v.max() - v.min()) / (v.max() + v.min())


def uniformity(img, region):
    """(integral, differential) uniformity in percent of img over region."""
    usable = _usable(region)
    if usable.sum() < 25:
        raise ValueError("the region holds fewer than 25 usable pixels")
    s = smooth(img)
    integral = _spread(s[usable])
    differential = 0.0
    for a in (s, s.T):
        mask = usable if a is s else usable.T
        for row, m in zip(a, mask):
            for i in range(row.size - 4):
                if m[i:i + 5].all():
                    differential = max(differential, _spread(row[i:i + 5]))
    return integral, differential
