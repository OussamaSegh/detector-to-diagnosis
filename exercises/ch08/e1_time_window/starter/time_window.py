# SPDX-License-Identifier: MIT
"""Exercise 8.1: the coincidence time window (Chapter 8)."""

SPEED_OF_LIGHT_MM_PER_PS = 0.299792458
FWHM_PER_SIGMA = 2.3548200450309493


def max_time_difference_ps(diameter_mm):
    """Largest |t1 - t2| for two back-to-back photons emitted inside a circle of this diameter."""
    raise NotImplementedError


def prompt_window_ps(diameter_mm, ctr_fwhm_ps, k):
    """Full width of the symmetric window |dt| <= max + k * sigma."""
    raise NotImplementedError


def true_fraction_kept(half_width_ps, offset_ps, ctr_fwhm_ps):
    """Probability that a true with real time difference offset_ps is measured inside the window."""
    raise NotImplementedError
