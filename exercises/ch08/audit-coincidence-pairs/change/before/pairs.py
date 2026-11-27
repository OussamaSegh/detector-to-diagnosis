# SPDX-License-Identifier: MIT
"""Coincidence tools of the Chapter 8 toolkit: singles and the rate of chance pairs."""
from collections import namedtuple

# One detected photon: when (ps), where (crystal index) and how much energy (keV).
Single = namedtuple("Single", "time_ps crystal energy_kev")


def expected_randoms_per_s(s1_per_s, s2_per_s, tau_s):
    """Chance pairs per second between two independent detectors, window |t1 - t2| <= tau."""
    return 2.0 * tau_s * s1_per_s * s2_per_s
