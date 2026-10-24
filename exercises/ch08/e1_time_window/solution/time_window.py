# SPDX-License-Identifier: MIT
"""Exercise 8.1: the coincidence time window (Chapter 8)."""

import math

SPEED_OF_LIGHT_MM_PER_PS = 0.299792458
FWHM_PER_SIGMA = 2.3548200450309493


# [snippet:window]
def max_time_difference_ps(diameter_mm):
    """Largest |t1 - t2| for two back-to-back photons emitted inside a circle of this diameter.

    An annihilation at distance x from the midpoint of its line of response gives
    dt = 2x / c. x is at most the radius, so |dt| <= diameter / c.
    """
    return diameter_mm / SPEED_OF_LIGHT_MM_PER_PS


def prompt_window_ps(diameter_mm, ctr_fwhm_ps, k):
    """Full width of the symmetric window |dt| <= max + k * sigma."""
    sigma = ctr_fwhm_ps / FWHM_PER_SIGMA
    return 2.0 * (max_time_difference_ps(diameter_mm) + k * sigma)


def true_fraction_kept(half_width_ps, offset_ps, ctr_fwhm_ps):
    """Probability that a true with real time difference offset_ps is measured inside the window.

    The measured difference is Gaussian around the real one with sigma = CTR / 2.3548.
    """
    sigma = ctr_fwhm_ps / FWHM_PER_SIGMA
    if sigma == 0.0:
        return 1.0 if abs(offset_ps) <= half_width_ps else 0.0

    def cdf(x):
        return 0.5 * (1.0 + math.erf(x / (sigma * math.sqrt(2.0))))

    return cdf(half_width_ps - offset_ps) - cdf(-half_width_ps - offset_ps)
# [/snippet:window]

# Why wider than 2.8 ns: the window must also absorb what this model leaves out.
# Board-to-board clock offsets and drift (Chapter 9), time walk at low energies (a
# leading-edge trigger fires later on a small pulse), the tails of the real timing
# distribution, which are not Gaussian, and the coarse time binning of some front-ends.
# Each needs margin, and how much is measured on the scanner, not computed (ask the
# detector team). The price of a wider window is linear: the
# randoms rate is proportional to the window width (Exercise 8.3).
