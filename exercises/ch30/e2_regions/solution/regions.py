# SPDX-License-Identifier: MIT
"""Exercise 30.2: contrast recovery and background variability from regions of interest.

An image is an n x n array; xs and ys, of the same shape, hold each pixel center's x and y in mm.
"""
import numpy as np


def disc(xs, ys, cx, cy, radius_mm):
    """The pixels whose centers are within radius_mm of (cx, cy)."""
    return np.hypot(xs - cx, ys - cy) <= radius_mm


def contrast_recovery(hot_mean, background_mean, true_ratio):
    """(hot / background - 1) / (true_ratio - 1): 1 for the true contrast, 0 for none."""
    return (hot_mean / background_mean - 1.0) / (true_ratio - 1.0)


def background_variability(image, xs, ys, centers, radius_mm):
    """(mean, variability): the mean of the regions' means, and the standard deviation of those
    means (K - 1 in the denominator) over their mean."""
    means = np.array([image[disc(xs, ys, cx, cy, radius_mm)].mean() for cx, cy in centers])
    m = float(means.mean())
    return m, float(means.std(ddof=1) / m)
