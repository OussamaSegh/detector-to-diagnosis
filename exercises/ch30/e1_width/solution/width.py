# SPDX-License-Identifier: MIT
"""Exercise 30.1: the full width of a peak at a fraction of its maximum (FWHM, FWTM)."""
import numpy as np


def peak(profile):
    """(position, value) of the peak: the vertex of the parabola through the highest sample and
    its two neighbors; the sample itself at either end of the profile or on a flat top."""
    p = np.asarray(profile, dtype=np.float64)
    k = int(p.argmax())
    if 0 < k < p.size - 1:
        a, b, c = p[k - 1], p[k], p[k + 1]
        curve = a - 2.0 * b + c
        if curve < 0.0:
            offset = 0.5 * (a - c) / curve
            return k + offset, b - 0.25 * (a - c) * offset
    return float(k), float(p[k])


def width(profile, step_mm, fraction=0.5):
    """The full width at fraction of the peak, in mm. Each side is interpolated linearly between
    the last sample above the level and the first below it. ValueError if the profile does not
    fall below the level on both sides."""
    p = np.asarray(profile, dtype=np.float64)
    _, top = peak(p)
    level = fraction * top
    k = int(p.argmax())
    lo = k
    while lo > 0 and p[lo] > level:
        lo -= 1
    hi = k
    while hi < p.size - 1 and p[hi] > level:
        hi += 1
    if p[lo] > level or p[hi] > level:
        raise ValueError(f"the profile does not fall to {fraction} of its peak on both sides")
    left = lo + (level - p[lo]) / (p[lo + 1] - p[lo])
    right = hi - (level - p[hi]) / (p[hi - 1] - p[hi])
    return float((right - left) * step_mm)
