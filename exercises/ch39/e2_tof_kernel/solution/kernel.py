# SPDX-License-Identifier: MIT
"""Exercise 39.2: the TOF kernel (solution)."""
import math

C_MM_PER_PS = 0.299792458


def sigma_mm(ctr_fwhm_ps):
    """The standard deviation along the line of the position given by a timing error of this
    FWHM: sigma_t = FWHM / (2 sqrt(2 ln 2)), and a time difference tau places the point at
    c tau / 2, so the position's sigma is c sigma_t / 2."""
    return ctr_fwhm_ps / (2.0 * math.sqrt(2.0 * math.log(2.0))) * C_MM_PER_PS / 2.0


def bin_edges_mm(bins, width_ps):
    """The bins + 1 edges along the line of the histogrammer's TOF bins: bin k holds tau in
    [(k - K/2) w, (k + 1 - K/2) w), and the position is c tau / 2."""
    w = width_ps * C_MM_PER_PS / 2.0
    return [(k - bins / 2.0) * w for k in range(bins + 1)]


def probabilities(position_mm, edges_mm, ctr_fwhm_ps):
    """The probability of each bin for a point at position_mm along the line: the Gaussian
    integrated over the bin, 0.5 (erf((hi - x) / (sqrt 2 sigma)) - erf((lo - x) / (sqrt 2 sigma))).
    Sampling the density at the bin's center is wrong whenever the bins are not much narrower
    than the kernel. Each edge's erf is computed once and shared by the two bins it bounds, so the
    probabilities of a point well inside add up to 1 to rounding."""
    z = math.sqrt(2.0) * sigma_mm(ctr_fwhm_ps)
    cdf = [0.5 * math.erf((e - position_mm) / z) for e in edges_mm]
    return [hi - lo for lo, hi in zip(cdf, cdf[1:])]
