# SPDX-License-Identifier: MIT
"""Exercise 30.2: contrast recovery and background variability from regions of interest.

An image is an n x n array; xs and ys, of the same shape, hold each pixel center's x and y in mm.
"""
import numpy as np


def disc(xs, ys, cx, cy, radius_mm):
    """The pixels whose centers are within radius_mm of (cx, cy)."""
    return np.hypot(xs - cx, ys - cy) <= radius_mm


def contrast_recovery(hot_mean, background_mean, true_ratio):
    """1 when the image shows the true contrast true_ratio of the hot region over the background."""
    return hot_mean / background_mean / true_ratio


def background_variability(image, xs, ys, centers, radius_mm):
    """(mean, variability) of the background: the mean of its regions, and how much the
    background varies, over that mean. Every pixel of every region counts."""
    mask = np.zeros(image.shape, dtype=bool)
    for cx, cy in centers:
        mask |= disc(xs, ys, cx, cy, radius_mm)
    m = float(image[mask].mean())
    return m, float(image[mask].std() / m)
