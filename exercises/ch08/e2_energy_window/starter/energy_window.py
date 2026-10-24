# SPDX-License-Identifier: MIT
"""Exercise 8.2: an energy window (Chapter 8)."""

ELECTRON_REST_ENERGY_KEV = 510.99895
FWHM_PER_SIGMA = 2.3548200450309493


def sigma_kev(resolution_fwhm):
    """Standard deviation of the 511 keV photopeak, in keV."""
    raise NotImplementedError


def photopeak_fraction(lo_kev, hi_kev, resolution_fwhm):
    """Fraction of fully absorbed 511 keV photons measured inside [lo, hi]."""
    raise NotImplementedError


def scattered_energy_kev(theta_deg, energy_kev=ELECTRON_REST_ENERGY_KEV):
    """Energy of the photon after one Compton scatter through theta."""
    raise NotImplementedError


def min_rejected_angle_deg(lo_kev):
    """Smallest scatter angle whose photon (measured exactly) falls below lo_kev."""
    raise NotImplementedError


def choose_window(resolution_fwhm):
    """Your window (lo, hi) in keV for this resolution."""
    raise NotImplementedError
