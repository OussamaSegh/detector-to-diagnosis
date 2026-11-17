# SPDX-License-Identifier: MIT
"""Exercise 39.4, a solution: how much time of flight should gain, and where.

The usual estimate of the gain in signal-to-noise ratio is sqrt(D / dx): D the length of the line
inside the object, dx the localization along the line, c / 2 times the timing resolution (FWHM).
D is not the same for every line through every point: through a point at radius r of a uniform
cylinder of radius R, a line at angle theta to the radius has the chord
2 sqrt(R^2 - r^2 sin^2 theta). Where the chord is shorter than dx, time of flight cannot localize
better than the object already does, and the line gains nothing.
"""
import numpy as np

C_MM_PER_PS = 0.299792458  # the speed of light


def localization_mm(ctr_ps):
    """The localization along a line, FWHM, for a timing resolution ctr_ps (FWHM)."""
    if ctr_ps <= 0:
        raise ValueError(f"timing resolution {ctr_ps} ps")
    return C_MM_PER_PS / 2.0 * ctr_ps


def chord_mm(r, theta, radius):
    """The length inside a cylinder of the given radius of the line through a point at r (r <=
    radius), at angle theta to the radius."""
    if not 0.0 <= r <= radius:
        raise ValueError(f"a point at {r} mm is outside a cylinder of {radius} mm")
    return 2.0 * np.sqrt(np.maximum(radius * radius - (r * np.sin(theta)) ** 2, 0.0))


def gain(r, radius, ctr_ps, angles=3600):
    """The estimated gain at a point at r. The noise variance at a point is taken as proportional to
    the mean, over the lines through it, of the length its counts are spread over: the chord D
    without time of flight, min(D, dx) with it. At the center it is sqrt(D / dx)."""
    dx = localization_mm(ctr_ps)
    theta = (np.arange(angles) + 0.5) * np.pi / angles
    d = chord_mm(r, theta, radius)
    return float(np.sqrt(np.mean(d) / np.mean(np.minimum(d, dx))))


def region_gain(points, radius, ctr_ps):
    """The gain of a measure over several regions whose noise adds: the ratio of the summed
    variances, so that a region with less gain counts for what it loses."""
    if not points:
        raise ValueError("no regions")
    g = np.array([gain(float(np.hypot(x, y)), radius, ctr_ps) for x, y in points])
    return float(1.0 / np.sqrt(np.mean(1.0 / g ** 2)))
