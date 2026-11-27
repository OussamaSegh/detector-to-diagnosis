# SPDX-License-Identifier: MIT
"""Coincidence tools of the Chapter 8 toolkit: singles and the rate of chance pairs."""
from bisect import bisect_right
from collections import namedtuple

# One detected photon: when (ps), where (crystal index) and how much energy (keV).
Single = namedtuple("Single", "time_ps crystal energy_kev")


def expected_randoms_per_s(s1_per_s, s2_per_s, tau_s):
    """Chance pairs per second between two independent detectors, window |t1 - t2| <= tau."""
    return 2.0 * tau_s * s1_per_s * s2_per_s


def find_pairs(singles, window_ps):
    """Every coincidence of the singles, taking all goods: each two singles of different
    crystals at most window_ps apart are one pair (first, second), first the earlier.
    Singles with equal times are ordered by crystal, then energy, so the result does not
    depend on the order the singles are given in."""
    ordered = sorted(singles, key=lambda s: s.time_ps)
    times = [s.time_ps for s in ordered]
    pairs = []
    for i, opener in enumerate(ordered):
        # Only (opener, later single): the pair is formed once, from its first single's window.
        for later in ordered[i + 1:bisect_right(times, opener.time_ps + window_ps)]:
            if later.crystal != opener.crystal:
                pairs.append((opener, later))
    return pairs
