# SPDX-License-Identifier: MIT
"""Coincidence tools of the Chapter 8 toolkit: singles and the rate of chance pairs."""
from bisect import bisect_left, bisect_right
from collections import namedtuple

# One detected photon: when (ps), where (crystal index) and how much energy (keV).
Single = namedtuple("Single", "time_ps crystal energy_kev")


def expected_randoms_per_s(s1_per_s, s2_per_s, tau_s):
    """Chance pairs per second between two independent detectors, window |t1 - t2| <= tau."""
    return 2.0 * tau_s * s1_per_s * s2_per_s


def find_pairs(singles, window_ps):
    """Every coincidence of the singles, taking all goods: each single opens a window of
    +/- window_ps, and every single of another crystal inside it makes a pair (first,
    second), first the earlier."""
    ordered = sorted(singles, key=lambda s: s.time_ps)
    times = [s.time_ps for s in ordered]
    pairs = []
    for i, s in enumerate(ordered):
        lo = bisect_left(times, s.time_ps - window_ps)
        hi = bisect_right(times, s.time_ps + window_ps)
        for j in range(lo, hi):
            other = ordered[j]
            if j == i or other.crystal == s.crystal:
                continue
            pairs.append((s, other) if i < j else (other, s))
    return pairs
