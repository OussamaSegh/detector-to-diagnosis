# SPDX-License-Identifier: MIT
"""Image quality figures of merit (Chapter 30), numpy only: the widths of a point's image, and the
contrast and noise of regions of interest, after the methods of NEMA NU 2 but in 2D.

NEMA NU 2 is the standard by which PET scanners are specified and compared. This module follows
its ideas, not its text: what a figure of merit means, and which choices change its value. The
choices are arguments here so that a test or a specification can fix them:

- a width: the peak by a parabola through the highest sample and its two neighbors, and each side
  by linear interpolation between the two samples around the level (half or a tenth of the peak);
- a profile through a point: summed over a band of pixels across the direction of measurement;
- a region of interest: the pixels whose centers are inside a circle;
- background variability: the spread of the means of several background regions of one size, not
  the spread of the pixels.
"""
import numpy as np


# [snippet:width]
def parabolic_peak(profile):
    """(index, value) of a profile's peak: the vertex of the parabola through the highest sample
    and its two neighbors. A peak on the first or last sample, or a flat top, is the sample."""
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
    """The full width of a profile's peak at fraction of its (parabolic) maximum, in mm: 0.5 is
    the FWHM, 0.1 the FWTM. Each side is linearly interpolated between the last sample above the
    level and the first below it. ValueError if the profile does not fall below the level on both
    sides of the peak: the profile is too short to measure the width."""
    p = np.asarray(profile, dtype=np.float64)
    _, top = parabolic_peak(p)
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
# [/snippet:width]


def point_profiles(image, half_band=1):
    """The two profiles through the brightest pixel of a point's image: along x (each row of the
    band summed) and along y (each column summed), each over 2 * half_band + 1 pixels across.
    For a point on the x axis, x is the radial direction and y the tangential one."""
    img = np.asarray(image, dtype=np.float64)
    j, i = np.unravel_index(int(img.argmax()), img.shape)
    rows = img[max(j - half_band, 0):j + half_band + 1, :].sum(axis=0)
    cols = img[:, max(i - half_band, 0):i + half_band + 1].sum(axis=1)
    return rows, cols


# [snippet:roi]
def disc(xs, ys, cx, cy, radius_mm):
    """The pixels whose centers are within radius_mm of (cx, cy), as a boolean mask."""
    return np.hypot(np.asarray(xs) - cx, np.asarray(ys) - cy) <= radius_mm


def contrast_recovery(hot_mean, background_mean, true_ratio):
    """CRC = (hot / background - 1) / (true_ratio - 1): 1 when the image has the true contrast.
    NEMA NU 2 reports it in percent as the hot sphere's percent contrast."""
    return (hot_mean / background_mean - 1.0) / (true_ratio - 1.0)


def background_variability(image, xs, ys, centers, radius_mm):
    """(mean, variability) of the background from regions of one radius at centers: the mean of
    the regions' means, and the standard deviation of those means (K - 1 in the denominator) over
    their mean. Pixel noise averages down in a region, so the variability depends on its size."""
    means = np.array([image[disc(xs, ys, cx, cy, radius_mm)].mean() for cx, cy in centers])
    m = float(means.mean())
    return m, float(means.std(ddof=1) / m)
# [/snippet:roi]


def place_background_rois(count, keep_out, inside_mm, radius_mm, spacing_mm=None, step_mm=2.0):
    """count centers for background regions of radius_mm: on a grid of step_mm, within inside_mm
    of the axis (the whole region inside), at least keep_out[k][2] from the k-th (x, y, distance),
    and spacing_mm apart (default 2 * radius_mm, so regions do not overlap). Chosen greedily from
    the axis outward, with ties broken by angle, so the same arguments always give the same
    centers. ValueError if they do not fit."""
    spacing = 2.0 * radius_mm if spacing_mm is None else spacing_mm
    g = np.arange(-inside_mm, inside_mm + step_mm / 2, step_mm)
    gx, gy = np.meshgrid(g, g, indexing="xy")
    gx, gy = gx.ravel(), gy.ravel()
    ok = np.hypot(gx, gy) + radius_mm <= inside_mm
    for x, y, d in keep_out:
        ok &= np.hypot(gx - x, gy - y) >= d
    order = np.lexsort((np.arctan2(gy, gx), np.round(np.hypot(gx, gy), 6)))
    chosen = []
    for k in order:
        if ok[k] and all(np.hypot(gx[k] - x, gy[k] - y) >= spacing for x, y in chosen):
            chosen.append((float(gx[k]), float(gy[k])))
            if len(chosen) == count:
                return chosen
    raise ValueError(f"only {len(chosen)} of {count} regions of {radius_mm} mm fit")
