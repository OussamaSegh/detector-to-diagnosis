# SPDX-License-Identifier: MIT
"""Exercise 27.3: calculated attenuation of an elliptical head outline, and the decay of a frame.

A line of response is given by its angle phi and its signed distance s from the center of the
field of view: the points p with p . (cos phi, sin phi) = s. Lengths are in mm.
"""
import numpy as np


def chords(s_mm, phi, a_mm, b_mm, center_mm=(0.0, 0.0), angle=0.0):
    """The length of each line inside the outline: a circle of the ellipse's mean radius."""
    s = np.asarray(s_mm, dtype=float)
    phi = np.asarray(phi, dtype=float)
    d = s - (center_mm[0] * np.cos(phi) + center_mm[1] * np.sin(phi))
    r = 0.5 * (a_mm + b_mm)
    return 2.0 * np.sqrt(np.clip(r ** 2 - d ** 2, 0.0, None))


def acf(chord_mm, mu_per_cm=0.096):
    """The attenuation correction factor of a line, exp(mu L)."""
    return np.exp(mu_per_cm * np.asarray(chord_mm, dtype=float))


def decay_factor(start_s, duration_s, half_life_s):
    """The factor that corrects a frame's counts for the decay since the reference time."""
    return np.exp(np.log(2.0) / half_life_s * start_s)
