# SPDX-License-Identifier: MIT
"""Exercise 39.1: where along the line (solution)."""
import math

C_MM_PER_PS = 0.299792458


def position(a, b, t_a_ps, t_b_ps):
    """The (x, y) of the annihilation on the line from crystal a to crystal b (mm), from the times
    each crystal saw its photon.

    A point at distance l from the middle, towards b, is L/2 + l from a and L/2 - l from b, so
    t_a - t_b = 2 l / c: l = c (t_a - t_b) / 2. The photon that arrived later travelled further,
    so the point is nearer the crystal that saw its photon first. A tau beyond the line's length
    (timing noise near a crystal) is clamped to the crystal."""
    ux, uy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(ux, uy)
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    ell = C_MM_PER_PS * (t_a_ps - t_b_ps) / 2.0
    ell = max(-length / 2.0, min(length / 2.0, ell))
    return mx + ell * ux / length, my + ell * uy / length


def tof_bin(tau_ps, bins, width_ps):
    """The TOF bin of tau = t_a - t_b, as MiniDAQ's histogrammer bins it, or None.

    floor((2 tau + K w) / 2w): integer arithmetic in the C++, a floor here, so that an edge goes
    to the bin above it and a negative tau is not rounded towards zero."""
    k = math.floor((2.0 * tau_ps + bins * width_ps) / (2.0 * width_ps))
    return k if 0 <= k < bins else None
