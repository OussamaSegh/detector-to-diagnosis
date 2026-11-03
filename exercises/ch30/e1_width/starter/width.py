# SPDX-License-Identifier: MIT
"""Exercise 30.1: the full width of a peak at a fraction of its maximum (FWHM, FWTM)."""
import numpy as np


def peak(profile):
    """(position, value) of the profile's maximum, in samples."""
    p = np.asarray(profile, dtype=np.float64)
    k = int(p.argmax())
    return float(k), float(p[k])


def width(profile, step_mm, fraction=0.5):
    """The full width at fraction of the maximum, in mm: the samples above the level, counted."""
    p = np.asarray(profile, dtype=np.float64)
    _, top = peak(p)
    return float(np.count_nonzero(p > fraction * top) * step_mm)
