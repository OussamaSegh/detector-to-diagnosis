# SPDX-License-Identifier: MIT
"""Exercise 30.4: the uniformity of an image of a uniform cylinder.

Two numbers, as the uniformity tests of nuclear medicine define them (NEMA's for gamma cameras,
used here on a transverse slice of a PET image of a uniform cylinder):

- integral uniformity, 100 (max - min) / (max + min) over the region;
- differential uniformity, the largest 100 (max - min) / (max + min) of any five consecutive
  pixels of a row or a column inside the region.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np

KERNEL = np.array([[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]]) / 16.0


def central_region(shape, center, radius_px, fraction=0.75):
    """The pixels within `fraction` of the cylinder's radius of its center (the central field)."""
    yy, xx = np.indices(shape)
    return np.hypot(xx - center[0], yy - center[1]) <= fraction * radius_px


def smooth(img):
    """The image convolved with KERNEL."""
    return np.asarray(img, dtype=float)


def _spread(v):
    return 100.0 * (v.max() - v.min()) / (v.max() + v.min())


def uniformity(img, region):
    """(integral, differential) uniformity in percent of img over region."""
    s = smooth(img)
    inside = s > 0  # the cylinder
    integral = _spread(s[inside])
    differential = 0.0
    for row in s:
        v = row[row > 0]
        for i in range(v.size - 4):
            differential = max(differential, _spread(v[i:i + 5]))
    return integral, differential
