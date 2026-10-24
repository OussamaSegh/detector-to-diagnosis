# SPDX-License-Identifier: MIT
"""Exercise 8.2: an energy window (Chapter 8)."""

import math

ELECTRON_REST_ENERGY_KEV = 510.99895
FWHM_PER_SIGMA = 2.3548200450309493


def sigma_kev(resolution_fwhm):
    """Standard deviation of the 511 keV photopeak, in keV."""
    return resolution_fwhm * ELECTRON_REST_ENERGY_KEV / FWHM_PER_SIGMA


def photopeak_fraction(lo_kev, hi_kev, resolution_fwhm):
    """Fraction of fully absorbed 511 keV photons measured inside [lo, hi]."""
    s = sigma_kev(resolution_fwhm)

    def cdf(x):
        return 0.5 * (1.0 + math.erf((x - ELECTRON_REST_ENERGY_KEV) / (s * math.sqrt(2.0))))

    return cdf(hi_kev) - cdf(lo_kev)


def scattered_energy_kev(theta_deg, energy_kev=ELECTRON_REST_ENERGY_KEV):
    """Energy of the photon after one Compton scatter through theta."""
    c = math.cos(math.radians(theta_deg))
    return energy_kev / (1.0 + (energy_kev / ELECTRON_REST_ENERGY_KEV) * (1.0 - c))


# [snippet:angle]
def min_rejected_angle_deg(lo_kev):
    """Smallest scatter angle whose photon (measured exactly) falls below lo_kev.

    For E = m_e c^2 the Compton formula is E' = E / (2 - cos theta), so
    cos theta = 2 - E / E'.
    """
    return math.degrees(math.acos(2.0 - ELECTRON_REST_ENERGY_KEV / lo_kev))
# [/snippet:angle]


# [snippet:choose]
def choose_window(resolution_fwhm):
    """Lower edge two sigma below the peak, but not below 425 keV; upper edge three sigma
    above, but not above 650 keV."""
    s = sigma_kev(resolution_fwhm)
    lo = max(425.0, ELECTRON_REST_ENERGY_KEV - 2.0 * s)
    hi = min(650.0, ELECTRON_REST_ENERGY_KEV + 3.0 * s)
    return lo, hi
# [/snippet:choose]

# Asymmetric: below the peak are the scattered photons, which the lower edge is there
# to reject, so it sits as close to the peak as the photopeak loss allows; above the
# peak there is little to reject (pile-up of two photons in one crystal), so the upper
# edge is wide and costs almost nothing.
# Scatter still passes: a photon that scattered through a small angle keeps most of its
# energy (30 degrees still leaves 450 keV), and the detector's own resolution smears
# scattered photons above any edge. An energy window reduces scatter; only a scatter
# correction in reconstruction removes what is left.
