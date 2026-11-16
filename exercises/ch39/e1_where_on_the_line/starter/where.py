# SPDX-License-Identifier: MIT
"""Exercise 39.1: where along the line (starter)."""
import math

C_MM_PER_PS = 0.299792458


def position(a, b, t_a_ps, t_b_ps):
    """The (x, y) of the annihilation on the line from crystal a to crystal b (mm), from the times
    each crystal saw its photon."""
    ux, uy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(ux, uy)
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    tau = t_a_ps - t_b_ps
    shift = C_MM_PER_PS * tau  # towards the crystal that saw its photon first
    return mx - shift * ux / length, my - shift * uy / length


def tof_bin(tau_ps, bins, width_ps):
    """The TOF bin of tau = t_a - t_b, as MiniDAQ's histogrammer bins it, or None."""
    k = round(tau_ps / width_ps) + bins // 2
    return k if 0 <= k < bins else None
