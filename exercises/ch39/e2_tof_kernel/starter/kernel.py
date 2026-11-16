# SPDX-License-Identifier: MIT
"""Exercise 39.2: the TOF kernel (starter)."""
import math

C_MM_PER_PS = 0.299792458


def sigma_mm(ctr_fwhm_ps):
    """The standard deviation along the line of the position given by a timing error of this
    FWHM."""
    return ctr_fwhm_ps / (2.0 * math.sqrt(2.0 * math.log(2.0))) * C_MM_PER_PS


def bin_edges_mm(bins, width_ps):
    """The bins + 1 edges along the line of the histogrammer's TOF bins."""
    w = width_ps * C_MM_PER_PS
    return [(k - bins / 2.0) * w for k in range(bins + 1)]


def probabilities(position_mm, edges_mm, ctr_fwhm_ps):
    """The probability of each bin for a point at position_mm along the line."""
    s = sigma_mm(ctr_fwhm_ps)
    out = []
    for lo, hi in zip(edges_mm, edges_mm[1:]):
        center = (lo + hi) / 2.0
        density = math.exp(-0.5 * ((center - position_mm) / s) ** 2) / (s * math.sqrt(2 * math.pi))
        out.append(density * (hi - lo))
    return out
