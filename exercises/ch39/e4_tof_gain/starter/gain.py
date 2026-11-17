# SPDX-License-Identifier: MIT
"""Exercise 39.4: how much time of flight should gain, and where.

The usual estimate of the gain in signal-to-noise ratio is sqrt(D / dx): D the length of the line
inside the object, dx the localization along the line (FWHM).

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np

C_MM_PER_PS = 0.299792458  # the speed of light


def localization_mm(ctr_ps):
    """The localization along a line, FWHM, for a timing resolution ctr_ps (FWHM)."""
    return C_MM_PER_PS * ctr_ps


def chord_mm(r, theta, radius):
    """The length inside the cylinder of the line through a point at r, at angle theta to the
    radius."""
    return 2.0 * radius


def gain(r, radius, ctr_ps, angles=3600):
    """The estimated gain at a point at r."""
    return float(np.sqrt(chord_mm(r, 0.0, radius) / localization_mm(ctr_ps)))


def region_gain(points, radius, ctr_ps):
    """The gain of a measure over several regions."""
    return float(np.mean([gain(float(np.hypot(x, y)), radius, ctr_ps) for x, y in points]))
