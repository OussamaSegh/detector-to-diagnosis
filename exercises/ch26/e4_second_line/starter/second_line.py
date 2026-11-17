# SPDX-License-Identifier: MIT
"""Exercise 26.4: a second energy line, the check that sees a wrong E_sat.

A crystal's code for a deposited energy E is c = g S(E) / 0.5 keV, with the sensor's saturation
S(E) = E_sat (1 - exp(-E / E_sat)). The calibration finds each crystal's gain g from its 511 keV
photopeak, with E_sat given from a bench measurement. A wrong E_sat still puts every photopeak at
511 keV.

This starter runs and its check passes every calibration. TODO: make the tests pass.
"""
import math

import numpy as np

ENERGY_LSB_KEV = 0.5
PEAK_KEV = 511.0
LINE_KEV = 307.0  # the lutetium-176 line of LYSO crystals, measured as Exercise 26.4 describes


def saturate(e_kev, e_sat):
    """The sensor's response to a deposited energy (identity for e_sat = inf)."""
    e = np.asarray(e_kev, dtype=float)
    if math.isinf(e_sat):
        return e
    return e_sat * -np.expm1(-e / e_sat)


def energy_of(code, code_511, e_sat):
    """The energy in keV of a code of a crystal whose photopeak is at code_511, for e_sat."""
    gain = np.asarray(code_511, dtype=float) * ENERGY_LSB_KEV / saturate(PEAK_KEV, e_sat)
    s = np.asarray(code, dtype=float) * ENERGY_LSB_KEV / gain
    if math.isinf(e_sat):
        return s
    return -e_sat * np.log1p(-s / e_sat)


def check_e_sat(e_sat, code_511, code_line, line_kev=LINE_KEV, tolerance=0.008):
    """(ok, energies, worst relative error): checks the calibration's curve on its photopeaks."""
    found = np.atleast_1d(energy_of(code_511, code_511, e_sat))
    err = np.abs(found / PEAK_KEV - 1.0)
    worst = float(err.max())
    return worst <= tolerance, found, worst


def estimate_e_sat(code_511, code_line, line_kev=LINE_KEV):
    """The E_sat that puts the line at its energy."""
    # A linear detector: the ratio of the codes is the ratio of the energies.
    return math.inf
